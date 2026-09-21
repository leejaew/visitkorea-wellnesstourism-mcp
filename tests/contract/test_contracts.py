import asyncio
import json
import logging
import unittest

import httpx

from mcp_server.config import Settings
from mcp_server.errors import WellnessAPIError
from mcp_server.server import create_server
from mcp_server.services import WellnessService


EXPECTED_TOOLS = {
    "get_legal_district_codes",
    "search_wellness_by_area",
    "search_wellness_by_location",
    "search_wellness_by_keyword",
    "get_wellness_sync_list",
    "get_wellness_common_info",
    "get_wellness_intro_info",
    "get_wellness_repeating_info",
    "get_wellness_images",
}


class _FakeClient:
    async def get_legal_district_codes(self, **kwargs) -> dict:
        return {
            "items": [{"lDongRegnCd": "11", "name": "Seoul"}],
            "numOfRows": kwargs.get("num_of_rows", 10),
            "pageNo": kwargs.get("page_no", 1),
            "totalCount": 1,
        }

    async def succeeds(self) -> dict:
        return {"items": []}

    async def invalid(self) -> dict:
        raise ValueError("bad input")

    async def upstream_failure(self) -> dict:
        raise WellnessAPIError("TIMEOUT", "Upstream API request timed out.")

    async def unexpected(self) -> dict:
        raise RuntimeError("secret internal detail")


SETTINGS = Settings(
    api_key="test-key",
    port=8080,
    allowed_hosts=("localhost",),
    allowed_origins=("http://localhost",),
)


def create_test_server():
    return create_server(
        SETTINGS,
        WellnessService(_FakeClient()),  # type: ignore[arg-type]
    )


class ContractTests(unittest.TestCase):
    def test_public_tool_names_remain_stable(self) -> None:
        mcp = create_test_server()
        tools = asyncio.run(mcp.list_tools())
        self.assertEqual({tool.name for tool in tools}, EXPECTED_TOOLS)

    def test_tool_schemas_expose_bounds(self) -> None:
        mcp = create_test_server()
        tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}
        expected_required = {
            "get_legal_district_codes": set(),
            "search_wellness_by_area": set(),
            "search_wellness_by_location": {"map_x", "map_y", "radius"},
            "search_wellness_by_keyword": {"keyword"},
            "get_wellness_sync_list": set(),
            "get_wellness_common_info": {"content_id"},
            "get_wellness_intro_info": {"content_id", "content_type_id"},
            "get_wellness_repeating_info": {"content_id", "content_type_id"},
            "get_wellness_images": {"content_id"},
        }
        for name, required in expected_required.items():
            with self.subTest(tool=name):
                schema = tools[name].inputSchema
                self.assertEqual(set(schema.get("required", [])), required)
                properties = schema["properties"]
                self.assertEqual(properties["lang_div_cd"]["default"], "KOR")
                self.assertEqual(properties["num_of_rows"]["default"], 10)
                self.assertEqual(properties["num_of_rows"]["minimum"], 1)
                self.assertEqual(properties["num_of_rows"]["maximum"], 100)
                self.assertEqual(properties["page_no"]["default"], 1)
                self.assertEqual(properties["page_no"]["minimum"], 1)
                self.assertEqual(properties["page_no"]["maximum"], 10_000)

        location = tools["search_wellness_by_location"].inputSchema["properties"]
        self.assertEqual(location["radius"]["maximum"], 20_000)
        self.assertEqual(location["radius"]["minimum"], 1)
        self.assertEqual(location["map_x"]["minimum"], -180)
        self.assertEqual(location["map_x"]["maximum"], 180)
        self.assertEqual(location["map_y"]["minimum"], -90)
        self.assertEqual(location["map_y"]["maximum"], 90)

        keyword = tools["search_wellness_by_keyword"].inputSchema["properties"][
            "keyword"
        ]
        self.assertEqual(keyword["minLength"], 1)
        self.assertEqual(keyword["maxLength"], 100)

        for name in (
            "get_wellness_common_info",
            "get_wellness_intro_info",
            "get_wellness_repeating_info",
            "get_wellness_images",
        ):
            self.assertEqual(
                tools[name].inputSchema["properties"]["content_id"]["pattern"],
                r"^\d{1,15}$",
            )

    def test_service_maps_expected_errors(self) -> None:
        service = WellnessService(_FakeClient())  # type: ignore[arg-type]
        invalid = asyncio.run(service.invoke("invalid"))
        upstream = asyncio.run(service.invoke("upstream_failure"))
        self.assertEqual(invalid["code"], "INVALID_PARAM")
        self.assertEqual(upstream["code"], "TIMEOUT")

    def test_service_sanitizes_unexpected_errors(self) -> None:
        service = WellnessService(_FakeClient())  # type: ignore[arg-type]
        with self.assertLogs(
            "mcp_server.services.wellness", level=logging.ERROR
        ) as logs:
            result = asyncio.run(service.invoke("unexpected"))
        self.assertEqual(result["code"], "INTERNAL_ERROR")
        self.assertNotIn("secret internal detail", result["message"])
        self.assertNotIn("secret internal detail", " ".join(logs.output))


class StreamableHttpContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_stateless_json_transport_lists_all_tools(self) -> None:
        mcp = create_test_server()
        app = mcp.streamable_http_app()
        transport = httpx.ASGITransport(app=app)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Host": "localhost",
        }
        initialize = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "contract-test", "version": "1.0"},
            },
        }
        list_tools = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        async with mcp.session_manager.run():
            async with httpx.AsyncClient(
                transport=transport, base_url="http://localhost"
            ) as client:
                init_response = await client.post(
                    "/mcp", headers=headers, content=json.dumps(initialize)
                )
                tools_response = await client.post(
                    "/mcp", headers=headers, content=json.dumps(list_tools)
                )

        self.assertEqual(init_response.status_code, 200)
        self.assertEqual(tools_response.status_code, 200)
        self.assertTrue(
            init_response.headers["content-type"].startswith("application/json")
        )
        self.assertNotIn("mcp-session-id", init_response.headers)
        payload = tools_response.json()
        names = {tool["name"] for tool in payload["result"]["tools"]}
        self.assertEqual(names, EXPECTED_TOOLS)

    async def test_tool_call_success_and_validation_error(self) -> None:
        mcp = create_test_server()
        app = mcp.streamable_http_app()
        transport = httpx.ASGITransport(app=app)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Host": "localhost",
        }
        success = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_legal_district_codes",
                "arguments": {"num_of_rows": 10, "page_no": 1},
            },
        }
        invalid = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "search_wellness_by_location",
                "arguments": {"map_x": 127, "map_y": 37.5, "radius": 0},
            },
        }

        async with mcp.session_manager.run():
            async with httpx.AsyncClient(
                transport=transport, base_url="http://localhost"
            ) as client:
                success_response = await client.post(
                    "/mcp", headers=headers, content=json.dumps(success)
                )
                invalid_response = await client.post(
                    "/mcp", headers=headers, content=json.dumps(invalid)
                )

        self.assertEqual(success_response.status_code, 200)
        self.assertFalse(success_response.json()["result"]["isError"])
        self.assertEqual(invalid_response.status_code, 200)
        self.assertTrue(invalid_response.json()["result"]["isError"])
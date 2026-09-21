import asyncio
import json
import logging
import unittest

import httpx

from api.parser import WellnessAPIError
from server import mcp
from services.wellness import WellnessService


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
    async def succeeds(self) -> dict:
        return {"items": []}

    async def invalid(self) -> dict:
        raise ValueError("bad input")

    async def upstream_failure(self) -> dict:
        raise WellnessAPIError("TIMEOUT", "Upstream API request timed out.")

    async def unexpected(self) -> dict:
        raise RuntimeError("secret internal detail")


class ContractTests(unittest.TestCase):
    def test_public_tool_names_remain_stable(self) -> None:
        tools = asyncio.run(mcp.list_tools())
        self.assertEqual({tool.name for tool in tools}, EXPECTED_TOOLS)

    def test_tool_schemas_expose_bounds(self) -> None:
        tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}
        location = tools["search_wellness_by_location"].inputSchema["properties"]
        self.assertEqual(location["radius"]["maximum"], 20_000)
        self.assertEqual(location["radius"]["minimum"], 1)
        self.assertEqual(location["num_of_rows"]["maximum"], 100)

    def test_service_maps_expected_errors(self) -> None:
        service = WellnessService(_FakeClient())  # type: ignore[arg-type]
        invalid = asyncio.run(service.invoke("invalid"))
        upstream = asyncio.run(service.invoke("upstream_failure"))
        self.assertEqual(invalid["code"], "INVALID_PARAM")
        self.assertEqual(upstream["code"], "TIMEOUT")

    def test_service_sanitizes_unexpected_errors(self) -> None:
        service = WellnessService(_FakeClient())  # type: ignore[arg-type]
        with self.assertLogs("services.wellness", level=logging.ERROR) as logs:
            result = asyncio.run(service.invoke("unexpected"))
        self.assertEqual(result["code"], "INTERNAL_ERROR")
        self.assertNotIn("secret internal detail", result["message"])
        self.assertNotIn("secret internal detail", " ".join(logs.output))


class StreamableHttpContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_stateless_json_transport_lists_all_tools(self) -> None:
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
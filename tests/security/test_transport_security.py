import logging
import unittest

import httpx
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mcp_server.config import Settings, create_http_client
from mcp_server.clients import MemorySharedState
from mcp_server.observability import RedactKeyFilter, configure_logging
from mcp_server.server import create_server
from mcp_server.services import WellnessService
from mcp_server.transports.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)


class TransportSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_security_headers_are_added(self) -> None:
        async def endpoint(request):
            return PlainTextResponse("ok")

        app = SecurityHeadersMiddleware(
            Starlette(routes=[Route("/", endpoint=endpoint)])
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost",
        ) as client:
            response = await client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])

    def test_log_filter_redacts_key_and_query_parameter(self) -> None:
        record = logging.LogRecord(
            "test",
            logging.INFO,
            __file__,
            1,
            "GET ?serviceKey=encoded-secret&contentId=1 encoded-secret",
            (),
            None,
        )
        RedactKeyFilter("encoded-secret").filter(record)
        message = record.getMessage()
        self.assertNotIn("encoded-secret", message)
        self.assertIn("serviceKey=[REDACTED]", message)

    def test_configured_application_logger_redacts_secret(self) -> None:
        configure_logging("encoded-secret")
        with self.assertLogs(
            "mcp_server.services.wellness", level=logging.ERROR
        ) as logs:
            logging.getLogger("mcp_server.services.wellness").error(
                "serviceKey=encoded-secret encoded-secret"
            )
        output = " ".join(logs.output)
        self.assertNotIn("encoded-secret", output)
        self.assertIn("[REDACTED]", output)

    async def test_rate_limit_rejects_excess_request(self) -> None:
        async def endpoint(request):
            return PlainTextResponse("ok")

        shared_state = MemorySharedState()
        app = RateLimitMiddleware(
            Starlette(routes=[Route("/mcp", endpoint=endpoint)]),
            shared_state,
            max_requests=1,
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost",
        ) as client:
            first = await client.get("/mcp")
            second = await client.get("/mcp")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.headers["retry-after"], "60")

    async def test_rate_limit_is_shared_across_middleware_instances(self) -> None:
        async def endpoint(request):
            return PlainTextResponse("ok")

        shared_state = MemorySharedState()
        inner = Starlette(routes=[Route("/mcp", endpoint=endpoint)])
        first_instance = RateLimitMiddleware(
            inner, shared_state, max_requests=1
        )
        second_instance = RateLimitMiddleware(
            inner, shared_state, max_requests=1
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=first_instance),
            base_url="http://localhost",
        ) as first_client:
            first = await first_client.get("/mcp")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=second_instance),
            base_url="http://localhost",
        ) as second_client:
            second = await second_client.get("/mcp")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)

    async def test_http_client_refuses_redirects(self) -> None:
        client = create_http_client()
        try:
            self.assertFalse(client.follow_redirects)
        finally:
            await client.aclose()

    async def test_mcp_rejects_untrusted_host_and_origin(self) -> None:
        class Client:
            pass

        settings = Settings(
            api_key="test",
            port=8080,
            allowed_hosts=("localhost",),
            allowed_origins=("http://localhost",),
        )
        server = create_server(
            settings, WellnessService(Client())  # type: ignore[arg-type]
        )
        app = server.streamable_http_app()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "security-test", "version": "1"},
            },
        }
        async with server.session_manager.run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://localhost",
            ) as client:
                bad_host = await client.post(
                    "/mcp",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Host": "evil.example",
                    },
                    json=payload,
                )
                bad_origin = await client.post(
                    "/mcp",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Host": "localhost",
                        "Origin": "https://evil.example",
                    },
                    json=payload,
                )
        self.assertGreaterEqual(bad_host.status_code, 400)
        self.assertGreaterEqual(bad_origin.status_code, 400)
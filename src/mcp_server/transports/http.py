from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.routing import Mount, Route

from mcp_server.clients import SharedState
from mcp_server.transports.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)


def create_http_app(
    server: FastMCP,
    http_client: httpx.AsyncClient,
    shared_state: SharedState,
    static_dir: Path,
):
    """Create the Streamable HTTP ASGI application and own its lifecycle."""
    mcp_http_app = server.streamable_http_app()

    async def serve_index(request: Request) -> FileResponse:
        return FileResponse(static_dir / "index.html")

    async def serve_favicon(request: Request) -> FileResponse:
        return FileResponse(static_dir / "favicon.png", media_type="image/png")

    @asynccontextmanager
    async def lifespan(app):
        try:
            await shared_state.open()
            async with server.session_manager.run():
                yield
        finally:
            if not http_client.is_closed:
                await http_client.aclose()
            await shared_state.close()

    app = Starlette(
        routes=[
            Route("/", endpoint=serve_index),
            Route("/favicon.png", endpoint=serve_favicon),
            Mount("/", app=mcp_http_app),
        ],
        lifespan=lifespan,
    )
    return RateLimitMiddleware(
        SecurityHeadersMiddleware(app),
        shared_state,
    )
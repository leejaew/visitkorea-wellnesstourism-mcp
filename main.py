import os
import uvicorn
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import FileResponse

from server import mcp

PORT = int(os.environ.get("PORT", 8080))


async def serve_index(request: Request) -> FileResponse:
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


async def serve_favicon(request: Request) -> FileResponse:
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "favicon.png"),
        media_type="image/png",
    )


# Build the streamable HTTP app (this also lazily initialises the session manager).
mcp_http_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app):
    # The StreamableHTTP session manager owns the anyio task group that handles
    # concurrent MCP sessions.  It must be running before any /mcp request
    # arrives; we wire it into the parent app's own lifespan so it starts
    # alongside uvicorn and stops cleanly on shutdown.
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/", endpoint=serve_index),
        Route("/favicon.png", endpoint=serve_favicon),
        Mount("/", app=mcp_http_app),
    ],
    lifespan=lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

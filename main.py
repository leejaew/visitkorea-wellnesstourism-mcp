import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from server import mcp

PORT = int(os.environ.get("PORT", 8080))


async def serve_index(request: Request) -> FileResponse:
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


mcp_sse_app = mcp.sse_app()

app = Starlette(
    routes=[
        Route("/", endpoint=serve_index),
        Mount("/", app=mcp_sse_app),
    ]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

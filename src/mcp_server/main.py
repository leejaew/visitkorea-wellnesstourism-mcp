import importlib.util
from pathlib import Path

import uvicorn

from mcp_server.clients import PostgresSharedState, WellnessClient
from mcp_server.config import Settings, create_http_client
from mcp_server.observability import configure_logging
from mcp_server.server import create_server
from mcp_server.services import WellnessService
from mcp_server.transports import create_http_app


def create_application(settings: Settings | None = None):
    """Compose dependencies and return the ASGI app plus runtime settings."""
    runtime_settings = settings or Settings.from_env()
    configure_logging(runtime_settings.api_key)
    http_client = create_http_client()
    shared_state = PostgresSharedState(runtime_settings.database_url)
    service = WellnessService(
        WellnessClient(runtime_settings.api_key, http_client, shared_state)
    )
    server = create_server(runtime_settings, service)
    static_dir = Path(__file__).resolve().parents[2] / "static"
    app = create_http_app(server, http_client, shared_state, static_dir)
    return app, runtime_settings


def run() -> None:
    app, settings = create_application()
    loop = "uvloop" if importlib.util.find_spec("uvloop") else "asyncio"
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        loop=loop,
        access_log=True,
    )
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import TransportSecuritySettings

from mcp_server.config import Settings
from mcp_server.services import WellnessService
from mcp_server.tools.registry import register_tools


def create_server(settings: Settings, service: WellnessService) -> FastMCP:
    """Construct the MCP protocol server without starting a transport."""
    server = FastMCP(
        "visitkorea-wellnesstourism",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(settings.allowed_hosts),
            allowed_origins=list(settings.allowed_origins),
        ),
        json_response=True,
        stateless_http=True,
    )
    register_tools(server, service)
    return server
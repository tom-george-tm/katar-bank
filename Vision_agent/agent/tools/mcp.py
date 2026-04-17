from google.adk.tools.mcp_toolset import McpToolset
from agent.core.config import settings

def get_mcp_tools() -> list:
    """
    Returns an ADK McpToolset if MCP_SERVICE_URL is configured.
    Enables the orchestrator to discover and call tools from a remote MCP server.
    """
    if not settings.MCP_SERVICE_URL:
        return []

    mcp_toolset = McpToolset(
        transport=settings.MCP_TRANSPORT,
        service_url=settings.MCP_SERVICE_URL,
        api_key=settings.MCP_API_KEY
    )
    return [mcp_toolset]

"""Remote MCP tool wiring for ADK agents.

Builds an ADK `McpToolset` from environment-backed settings so the agent can
discover and call tools exposed by a remote MCP server.
"""

from __future__ import annotations

from typing import List

from agent.core import settings
from agent.exceptions import ToolConfigurationException


def _build_headers() -> dict[str, str] | None:
    """Return request headers for the remote MCP server, if configured."""
    api_key = settings.MCP_API_KEY.strip()
    if not api_key:
        return None
    return {"Authorization": f"Bearer {api_key}"}


def get_mcp_tools() -> List[object]:
    """Return a remote MCP toolset when MCP integration is configured."""
    service_url = settings.MCP_SERVICE_URL.strip()
    if not service_url:
        return []

    try:
        from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams, StreamableHTTPServerParams  # type: ignore[import-not-found]
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - defensive
        raise ToolConfigurationException(
            "Failed to import ADK MCP tool support. Ensure the installed "
            "`google-adk` version includes `google.adk.tools.mcp_tool`."
        ) from exc

    headers = _build_headers()
    transport = settings.MCP_TRANSPORT.lower().strip()

    if transport == "sse":
        connection_params = SseServerParams(url=service_url, headers=headers)
    elif transport == "streamable_http":
        connection_params = StreamableHTTPServerParams(
            url=service_url,
            headers=headers,
        )
    else:
        raise ToolConfigurationException(
            "Invalid MCP_TRANSPORT value. Use `sse` or `streamable_http`."
        )

    return [McpToolset(connection_params=connection_params)]

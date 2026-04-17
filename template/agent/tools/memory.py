"""Memory-related tools for ADK agents.

Currently exposes a helper that returns the list of tools to attach when
memory is enabled (for example, the built-in `load_memory` tool).
"""

from __future__ import annotations

from typing import List

from agent.exceptions import ToolConfigurationException


def get_memory_tools(memory_service) -> List[object]:
    """Return tools that enable agents to query long-term memory.

    - When `memory_service` is None, returns an empty list (memory disabled).
    - When `memory_service` is set, attempts to import and return ADK's
      built-in `load_memory` tool. If the import fails, raises a
      ToolConfigurationException so misconfiguration is visible.
    """
    if memory_service is None:
        return []

    try:
        from google.adk.tools import load_memory  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - defensive
        raise ToolConfigurationException(
            "Failed to import google.adk.tools.load_memory while MEMORY_SERVICE_BACKEND "
            "is enabled. Ensure the ADK tools package is installed and compatible."
        ) from exc

    return [load_memory]


"""Prompt and instruction text for the root orchestrator agent."""


def get_orchestrator_instruction(has_tools: bool) -> str:
    """Return the orchestrator instruction based on available root tools."""
    if has_tools:
        return (
            "You are an orchestrator. Delegate to your sub-agents based on the "
            "user request. Use the load_memory tool when past context might help. "
            "Use MCP tools when the task requires external systems exposed by the "
            "configured MCP server."
        )

    return "You are an orchestrator. Delegate to your sub-agents based on the user request."

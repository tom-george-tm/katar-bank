"""Prompt and description for the remote sub-agent.

Use this for documentation and for the description passed to RemoteA2aAgent.
The remote agent runs in a separate service; its instructions are defined there.
"""

# Description for routing: tells the orchestrator when to call this remote agent.
DEFAULT_DESCRIPTION = "Handles specialized tasks via a remote A2A agent service (e.g. search, tools)."

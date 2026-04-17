"""Remote sub-agent definition.

This agent is a proxy to another A2A server (different process/URL).
The actual behavior and prompts are defined in that remote service.
Description for routing lives in prompt.py.
"""

from agent.core import settings
from agent.sub_agents.remote_agent.prompt import DEFAULT_DESCRIPTION
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

remote_agent = RemoteA2aAgent(
    name="remote_sub_agent",
    description=DEFAULT_DESCRIPTION,
    agent_card=settings.REMOTE_A2A_AGENT_URL,  # URL where the remote agent serves its A2A interface
)

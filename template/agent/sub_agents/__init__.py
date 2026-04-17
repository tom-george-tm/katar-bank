"""Sub-agents used by the root agent.

- example_agent: local Agent (same process).
- remote_agent: RemoteA2aAgent (separate A2A service).
"""

from agent.sub_agents.example_agent.sub_agent import example_agent
from agent.sub_agents.remote_agent.sub_agent import remote_agent

__all__ = ["example_agent", "remote_agent"]

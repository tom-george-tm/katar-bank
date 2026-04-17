"""Example (local) sub-agent definition.

This agent runs in the same process as the root agent. Use for logic that doesn't
need a separate service. Instruction text lives in prompt.py.
"""

from agent.core.model import get_model
from agent.sub_agents.example_agent.prompt import DEFAULT_INSTRUCTION
from google.adk.agents import Agent

example_agent = Agent(
    name="example_sub_agent",
    model=get_model(),
    description="Handles general questions and simple tasks locally.",
    instruction=DEFAULT_INSTRUCTION,
    tools=[],  # Add tools here if this sub-agent needs them (e.g. MCPToolset or custom tools from agent.tools).
)

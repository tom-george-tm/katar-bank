"""Entry point: root workflow agent, services, runner, and A2A app.

- Session (state): Runner uses session_service for conversation state and history.
- Memory: Runner uses memory_service for long-term knowledge; we add after_agent_callback
  to ingest each turn into memory, and optionally the load_memory tool so the agent can query it.
- Artifact: Runner uses artifact_service; tools/agents use context.save_artifact / load_artifact.

The root agent is implemented as an ADK **workflow agent**. We default to a
`SequentialAgent` that runs a single orchestrator LLM agent, and include
commented examples for `ParallelAgent` and `LoopAgent` usage following ADK docs.
"""

from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent.core import get_model, instrument_fastapi, settings, setup_opentelemetry
from agent.core.artifact_management import get_artifact_service
from agent.core.memory_management import get_memory_service
from agent.prompt import get_orchestrator_instruction
from agent.core.state_management import get_session_service
from agent.sub_agents import example_agent, remote_agent
from agent.tools import get_mcp_tools, get_memory_tools
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from google.adk.agents.sequential_agent import SequentialAgent
# from google.adk.agents.parallel_agent import ParallelAgent  # Example only (see below)
# from google.adk.agents import LoopAgent  # Example only (see below)
from google.adk.runners import Runner

# 1. Initialize OTEL first (before Runner/agents so ADK built-in spans are exported).
setup_opentelemetry()

# =======================================================================
# --- 1. SESSION, MEMORY & ARTIFACT (env-configured) ---
# =======================================================================
# Session: conversation state and history (Runner loads/saves via session_service).
# Memory: long-term knowledge; ingest via add_session_to_memory, query via load_memory tool.
# Artifact: binary blobs; tools use context.save_artifact / load_artifact (Runner provides artifact_service).
session_service = get_session_service()
memory_service = get_memory_service()
artifact_service = get_artifact_service()


def _make_after_agent_callback(mem_svc):
    """Build callback that ingests the current session into long-term memory after each turn."""

    async def _after_agent(callback_context):
        inv = getattr(callback_context, "_invocation_context", None)
        if inv is None or mem_svc is None:
            return
        session = getattr(inv, "session", None)
        if session is not None:
            await mem_svc.add_session_to_memory(session)

    return _after_agent


# Root agent tools: use helpers so optional memory/MCP tools live under
# agent/tools/ and can be configured from env without changing agent wiring.
_root_tools = [
    *get_memory_tools(memory_service),
    *get_mcp_tools(),
]

# =======================================================================
# --- 2. ORCHESTRATOR AGENT (LLM) ---
# =======================================================================
orchestrator_agent = Agent(
    name="orchestrator_agent",
    model=get_model(),
    description=settings.AGENT_DESCRIPTION,
    instruction=get_orchestrator_instruction(bool(_root_tools)),
    tools=_root_tools,
    sub_agents=[example_agent, remote_agent],
    after_agent_callback=_make_after_agent_callback(memory_service) if memory_service else None,
)

# =======================================================================
# --- 3. ROOT WORKFLOW AGENT (Sequential) ---
# =======================================================================
# By default we use a SequentialAgent so the control flow is explicit and
# matches ADK's workflow agent patterns. This runs the orchestrator agent
# as a single step, but you can extend the sub_agents list to add more
# fixed steps in the future.
root_agent = SequentialAgent(
    name=settings.AGENT_NAME,
    sub_agents=[orchestrator_agent],
    description="Sequential workflow: runs the orchestrator agent (and, if added, other fixed steps) in order.",
)

# -----------------------------------------------------------------------
# Alternative workflows (commented out examples)
# -----------------------------------------------------------------------
# Parallel workflow example (run multiple orchestrators or pipelines in parallel):
# parallel_root_agent = ParallelAgent(
#     name=f"{settings.AGENT_NAME}_parallel",
#     sub_agents=[orchestrator_agent],  # e.g. [example_agent, remote_agent] or other agents
#     description="Parallel workflow example (commented out by default).",
# )
#
# Loop workflow example (iterative refinement with a LoopAgent):
# loop_root_agent = LoopAgent(
#     name=f"{settings.AGENT_NAME}_loop",
#     sub_agents=[orchestrator_agent],  # typically a small pipeline for refinement
#     max_iterations=5,
# )

runner_kw: dict = {
    "agent": root_agent,
    "app_name": settings.AGENT_NAME,
    "session_service": session_service,
}
if memory_service is not None:
    runner_kw["memory_service"] = memory_service
if artifact_service is not None:
    runner_kw["artifact_service"] = artifact_service
runner = Runner(**runner_kw)

# =======================================================================
# --- 4. AGENT CARD (A2A METADATA) ---
# =======================================================================
agent_card: AgentCard = AgentCard(
    capabilities=AgentCapabilities(),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    description=settings.AGENT_DESCRIPTION,
    name=settings.AGENT_NAME,
    url=settings.CLOUD_RUN_URL,
    version=settings.AGENT_VERSION,
    preferred_transport="JSONRPC",
    protocol_version="0.3.0",
    supports_authenticated_extended_card=True,
    skills=[
        AgentSkill(
            name="Orchestration",
            description="Delegates to example and remote sub-agents.",
            id="orchestrator",
            tags=["llm", "orchestration"],
        ),
    ],
)

# =======================================================================
# --- 5. APP WRAPPING & EXECUTION ---
# =======================================================================
a2a_app = to_a2a(
    root_agent,
    runner=runner,
    host="0.0.0.0",
    port=settings.PORT,
    agent_card=agent_card,
)

instrument_fastapi(a2a_app)


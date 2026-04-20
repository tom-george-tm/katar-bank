"""Vision Agent: Root workflow agent, services, runner, and A2A app.

This module unifies the Vision processing tools into a production-ready ADK orchestrator.
Supports Orchestrator, Sequential, and Parallel workflow modes.
"""

import contextvars
import logging
import os
import uuid
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent.core import (
    get_artifact_service,
    get_memory_service,
    get_model,
    get_session_service,
    instrument_fastapi,
    settings,
    setup_opentelemetry,
)
from agent.core.schema_contract import get_input_schema_model, get_output_schema_model
from agent.core.schema_validation import install_schema_validation_middleware
from agent.exceptions.base import APIException
from agent.prompts.root_agent import ORCHESTRATOR_SYSTEM_INSTRUCTION
from agent.remote_agents import remote_agents as configured_remote_agents
from agent.tools import (
    document_ocr_tool,
    download_gcs_tool,
    gemini_vision_tool,
    get_memory_tools,
    get_vision_instructions_tool,
    preprocess_tool,
)
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.runners import Runner

# =======================================================================
# --- 0. LOGGING & CONTEXT ---
# =======================================================================
REQUEST_ID_CTX: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = REQUEST_ID_CTX.get() or "-"
        return True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s [%(request_id)s] - %(message)s",
)
for _handler in logging.getLogger().handlers:
    _handler.addFilter(_RequestIdFilter())

logger = logging.getLogger(__name__)

# Initialize OTEL first to capture ADK internal spans
setup_opentelemetry()

# =======================================================================
# --- 1. CORE SERVICES (Session, Memory & Artifact) ---
# =======================================================================
session_service = get_session_service()
memory_service = get_memory_service()
artifact_service = get_artifact_service()

def _make_after_agent_callback(mem_svc):
    """Callback to ingest the current session into long-term memory after each turn."""
    async def _after_agent(callback_context):
        inv = getattr(callback_context, "_invocation_context", None)
        if inv is None or mem_svc is None:
            return
        session = getattr(inv, "session", None)
        if session is not None:
            await mem_svc.add_session_to_memory(session)
    return _after_agent

# Root agent tools: Vision suite + infrastructure helpers
_root_tools = [
    download_gcs_tool,
    preprocess_tool,
    document_ocr_tool,
    get_vision_instructions_tool,
    gemini_vision_tool,
    *get_memory_tools(memory_service)
]

WORKFLOW_MODE = "orchestrator"

# =======================================================================
# --- 2. ORCHESTRATOR AGENT (Vision Logic) ---
# Used in: orchestrator, sequential modes
# =======================================================================


if WORKFLOW_MODE in ("orchestrator", "sequential"):
    orchestrator_agent = Agent(
        name="vision_orchestrator",
        model=get_model(),
        description=settings.AGENT_DESCRIPTION,
        instruction=ORCHESTRATOR_SYSTEM_INSTRUCTION,
        tools=_root_tools,
        sub_agents=configured_remote_agents,
        after_agent_callback=_make_after_agent_callback(memory_service) if memory_service else None,
    )


root_agent = orchestrator_agent


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
# --- 4. AGENT CARD (A2A Metadata) ---
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
        AgentSkill(name="Document OCR", description="Extracts text/forms via DocAI", id="ocr"),
        AgentSkill(name="Vision Reasoning", description="Semantic extraction via Gemini", id="vision"),
    ],
)

# =======================================================================
# --- 5. A2A APP EXPORT & INSTRUMENTATION ---
# =======================================================================
a2a_app = to_a2a(
    root_agent,
    runner=runner,
    host="0.0.0.0",
    port=settings.PORT,
    agent_card=agent_card,
)

# --- Middleware ---
@a2a_app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or request.headers.get("uuid") or str(uuid.uuid4())
    request.state.request_id = request_id
    REQUEST_ID_CTX.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# OTEL instrumentation
instrument_fastapi(a2a_app)
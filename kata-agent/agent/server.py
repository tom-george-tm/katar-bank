import uvicorn
import logging
from starlette.applications import Starlette
from a2a.server.routes import create_jsonrpc_routes, create_agent_card_routes
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, AgentInterface

from agent.core.config import settings
from agent.core.otel import (
    setup_opentelemetry,
    instrument_fastapi,
)
from agent.executor import VisionAgentExecutor

logger = logging.getLogger(__name__)

setup_opentelemetry()

vision_skill = AgentSkill(
    id="process_document",
    name="Process Document",
    description=(
        "Executes intelligent document processing using OCR and Large Multimodal Models (Gemini). "
        "Supports three flows: OCR only (ocr_pipeline), Vision only (vision_pipeline), or combined (ocr_vision_pipeline). "
        "Inputs can be an attached file (binary) or a GCS URI. Supports custom prompts and JSON extraction schemas."
    ),
    tags=["ocr", "vision", "document processing", "extraction", "gemini"],
    input_modes=["application/json", "multipart/form-data"],
    output_modes=["application/json"],
)

agent_card = AgentCard(
    name=settings.AGENT_NAME,
    description=settings.AGENT_DESCRIPTION,
    version=settings.AGENT_VERSION,
    supported_interfaces=[
        AgentInterface(
            url="http://localhost:8000/rpc",
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        )
    ],
    default_input_modes=["application/json"],
    default_output_modes=["application/json"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[vision_skill],
)

request_handler = DefaultRequestHandler(
    agent_executor=VisionAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

agent_card_routes = create_agent_card_routes(agent_card)
jsonrpc_routes = create_jsonrpc_routes(request_handler, "/rpc")

app = Starlette(
    routes=agent_card_routes + jsonrpc_routes
)

instrument_fastapi(app)

if __name__ == "__main__":
    logger.info(f"Starting A2A Vision Agent: {settings.AGENT_NAME} v{settings.AGENT_VERSION}")
    logger.info(f"JSON-RPC endpoint: http://0.0.0.0:{settings.PORT}/rpc")
    logger.info(f"Agent card endpoint: http://0.0.0.0:{settings.PORT}/.well-known/agent.json")
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)

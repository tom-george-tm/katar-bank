import uvicorn
import logging
from starlette.applications import Starlette
from starlette.routing import Route
from a2a.server.routes import create_jsonrpc_routes, create_agent_card_routes
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent.core.config import settings
from agent.core.otel import (
    setup_opentelemetry,
    instrument_fastapi,
)
from agent.executor import VisionAgentExecutor

logger = logging.getLogger(__name__)

# Initialize OTEL first
setup_opentelemetry()

# Define the Vision Agent's capability using AgentSkill
vision_skill = AgentSkill(
    id="process_document",
    name="Process Document",
    description=(
        "Executes intelligent document processing using OCR and Large Multimodal Models (Gemini). "
        "Supports three flows: OCR only (ocr_pipeline), Vision only (vision_pipeline), or combined (ocr_vision_pipeline). "
        "Inputs can be an attached file (binary) or a GCS URI. Supports custom prompts and JSON extraction schemas."
    ),
    tags=["ocr", "vision", "document processing", "extraction", "gemini"],
    # examples=[
    #     {
    #         "flow_type": "ocr_vision_pipeline",
    #         "processor_type": "form_parser",
    #         "custom_prompt": "Extract all billing details from this invoice.",
    #         "extraction_schema": {
    #             "type": "object",
    #             "properties": {
    #                 "bill_to": {"type": "string"},
    #                 "total_amount": {"type": "number"}
    #             }
    #         }
    #     }
    # ],
    input_modes=["application/json", "multipart/form-data"],
    output_modes=["application/json"],
)

# Define the public-facing agent card
agent_card = AgentCard(
    name=settings.AGENT_NAME,
    description=settings.AGENT_DESCRIPTION,
    url=settings.CLOUD_RUN_URL,
    version=settings.AGENT_VERSION,
    default_input_modes=["application/json"],
    default_output_modes=["application/json"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[vision_skill],
)

# Create the request handler with our specific executor and agent card
request_handler = DefaultRequestHandler(
    agent_executor=VisionAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

# Create routes for the A2A server
agent_card_routes = create_agent_card_routes(agent_card)
jsonrpc_routes = create_jsonrpc_routes(request_handler, "/rpc")

# Build the Starlette application
app = Starlette(
    routes=agent_card_routes + jsonrpc_routes
)

# Instrument FastAPI after creation
instrument_fastapi(app)

if __name__ == "__main__":
    logger.info(f"Starting A2A Vision Agent: {settings.AGENT_NAME} v{settings.AGENT_VERSION}")
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)

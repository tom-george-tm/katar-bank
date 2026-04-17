import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PORT: int
    MCP_SERVICE_URL: str = ""
    MCP_TRANSPORT: str = "sse"
    MCP_API_KEY: str = ""

    AGENT_NAME: str
    AGENT_DESCRIPTION: str
    AGENT_VERSION: str
    CLOUD_RUN_URL: str
    GOOGLE_CLOUD_PROJECT: str = ""  # GCP project for Vertex AI, Cloud Trace, etc.
    GOOGLE_GENAI_USE_VERTEXAI: str = ""  # forwarded to google-genai client via env
    ENABLE_CLOUD_TRACE: bool = False  # when True, export OTEL traces to Cloud Trace

    # -------------------------------------------------------------------------
    # Model provider - see agent/core/model/provider.py
    # -------------------------------------------------------------------------
    LLM_PROVIDER: str = "vertex_ai"  # vertex_ai | garden
    LLM_MODEL: str = "gemini-2.0-flash"  # model name for vertex_ai (e.g. gemini-2.0-flash)
    VERTEX_AI_LOCATION: str = "us-central1"  # used for Vertex AI and for garden (with project + endpoint id)
    # Garden only: endpoint id; path = projects/GOOGLE_CLOUD_PROJECT/locations/VERTEX_AI_LOCATION/endpoints/GARDEN_ENDPOINT_ID
    GARDEN_ENDPOINT_ID: str = ""

    REMOTE_A2A_AGENT_URL: str = "http://localhost:8001"

    # -------------------------------------------------------------------------
    # State (session) management - ADK BaseSessionService
    # See agent/core/state_management/factory.py
    # -------------------------------------------------------------------------
    SESSION_SERVICE_BACKEND: str = "inmemory"  # inmemory | firestore | redis | postgres | mongodb | memorystore

    # Firestore (when SESSION_SERVICE_BACKEND=firestore) – kept separate from other GCP config
    FIRESTORE_PROJECT: str = ""
    FIRESTORE_DATABASE: str = "(default)"
    FIRESTORE_LOCATION: str = ""  # Optional: database region (e.g. us-central1); for reference / future use
    # Redis (when SESSION_SERVICE_BACKEND=redis or memorystore)
    REDIS_URL: str = "redis://localhost:6379/0"
    MEMORYSTORE_REDIS_URL: str = ""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    # Postgres (when SESSION_SERVICE_BACKEND=postgres) - use an async SQLAlchemy URL
    POSTGRES_URI: str = ""
    # MongoDB (when SESSION_SERVICE_BACKEND=mongodb)
    MONGODB_URI: str = ""
    MONGODB_DATABASE: str = "adk"
    MONGODB_SESSIONS_COLLECTION: str = "sessions"

    # -------------------------------------------------------------------------
    # Memory management - ADK BaseMemoryService (long-term knowledge)
    # See agent/core/memory_management/factory.py
    # -------------------------------------------------------------------------
    MEMORY_SERVICE_BACKEND: str = "inmemory"  # inmemory | redis | none
    # Redis long-term memory (when MEMORY_SERVICE_BACKEND=redis) – requires adk-redis[memory] + Agent Memory Server
    REDIS_MEMORY_API_BASE_URL: str = "http://localhost:8088"  # Redis Agent Memory Server URL
    REDIS_MEMORY_NAMESPACE: str = "adk_app"
    REDIS_MEMORY_EXTRACTION_STRATEGY: str = "discrete"  # discrete | ...
    REDIS_MEMORY_RECENCY_BOOST: bool = True

    # -------------------------------------------------------------------------
    # Artifact management - ADK BaseArtifactService
    # See agent/core/artifact_management/factory.py
    # -------------------------------------------------------------------------
    ARTIFACT_SERVICE_BACKEND: str = "inmemory"  # inmemory | gcs | none
    GCS_ARTIFACT_BUCKET: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

# -------------------------------------------------------------------------
# Propagate key settings into process env for google-genai / Vertex AI.
# This ensures google.genai.Client sees the correct backend and project
# even when they are only set in .env (not exported in the shell).
# -------------------------------------------------------------------------
if settings.GOOGLE_CLOUD_PROJECT:
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", settings.GOOGLE_CLOUD_PROJECT)

if settings.VERTEX_AI_LOCATION:
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", settings.VERTEX_AI_LOCATION)

if settings.GOOGLE_GENAI_USE_VERTEXAI:
    os.environ.setdefault(
        "GOOGLE_GENAI_USE_VERTEXAI", settings.GOOGLE_GENAI_USE_VERTEXAI
    )

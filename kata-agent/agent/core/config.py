import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Server ---
    PORT: int = 8000

    # --- Agent Metadata ---
    AGENT_NAME: str = "Vision Agent"
    AGENT_DESCRIPTION: str = ""
    AGENT_VERSION: str = "1.0.0"
    CLOUD_RUN_URL: str = ""

    # --- Google Cloud Core ---
    GOOGLE_CLOUD_PROJECT: str  # GCP project ID (mandatory)
    CREDENTIALS_PATH: str      # Path to service account JSON (mandatory)

    # --- Vertex AI (Vision) ---
    VERTEX_AI_LOCATION: str = "us-central1"
    LLM_MODEL: str = "gemini-2.0-flash"
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192

    # --- Document AI (OCR) ---
    DOCAI_LOCATION: str = "us"
    DOCAI_FORM_PARSER_ID: str = ""
    DOCAI_DOCUMENT_OCR_ID: str = ""
    DOCAI_LAYOUT_PARSER_ID: str = ""

    # --- ADK Services ---
    SESSION_SERVICE_BACKEND: str = "inmemory"
    MEMORY_SERVICE_BACKEND: str = "inmemory"
    ARTIFACT_SERVICE_BACKEND: str = "inmemory"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# -------------------------------------------------------------------------
# Propagate critical settings into process env for Google SDKs.
# This ensures libraries like google-genai and Document AI clients 
# see the correct project and location even when not explicitly passed.
# -------------------------------------------------------------------------
if settings.GOOGLE_CLOUD_PROJECT:
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", settings.GOOGLE_CLOUD_PROJECT)
    # Some older GCP libs look for GCP_PROJECT_ID
    os.environ.setdefault("GCP_PROJECT_ID", settings.GOOGLE_CLOUD_PROJECT)

if settings.VERTEX_AI_LOCATION:
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", settings.VERTEX_AI_LOCATION)

if settings.CREDENTIALS_PATH:
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.CREDENTIALS_PATH)

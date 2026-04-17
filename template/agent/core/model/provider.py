"""Model provider for ADK: resolve model from env (Vertex AI or Model Garden).

The main entrypoint is `get_model()`, which returns the value to pass to
Agent(model=...) based on LLM_PROVIDER:

- LLM_PROVIDER=vertex_ai (default) -> model name (e.g. gemini-2.0-flash).
  Use GOOGLE_GENAI_USE_VERTEXAI=TRUE, GOOGLE_CLOUD_PROJECT, VERTEX_AI_LOCATION.
- LLM_PROVIDER=garden -> full endpoint path built from GOOGLE_CLOUD_PROJECT +
  VERTEX_AI_LOCATION + GARDEN_ENDPOINT_ID.
"""

from __future__ import annotations

from agent.core.config import settings
from agent.core.model.types import ModelProvider


def get_model() -> str:
    """
    Return the model identifier for ADK Agent(model=...) from env.

    - vertex_ai: returns LLM_MODEL. Set GOOGLE_GENAI_USE_VERTEXAI=TRUE,
      GOOGLE_CLOUD_PROJECT, VERTEX_AI_LOCATION.
    - garden: builds path from GOOGLE_CLOUD_PROJECT + VERTEX_AI_LOCATION +
      GARDEN_ENDPOINT_ID (all from env).
    """
    raw = (settings.LLM_PROVIDER or "vertex_ai").strip().lower()
    try:
        provider = ModelProvider(raw)
    except ValueError:
        raise ValueError(
            f"Invalid LLM_PROVIDER={raw!r}. Use 'vertex_ai' or 'garden'."
        ) from None

    if provider == ModelProvider.VERTEX_AI:
        return (settings.LLM_MODEL or "gemini-2.0-flash").strip()

    if provider == ModelProvider.GARDEN:
        project = (settings.GOOGLE_CLOUD_PROJECT or "").strip()
        location = (settings.VERTEX_AI_LOCATION or "us-central1").strip()
        endpoint_id = (settings.GARDEN_ENDPOINT_ID or "").strip()
        if not project or not endpoint_id:
            raise ValueError(
                "For LLM_PROVIDER=garden set GOOGLE_CLOUD_PROJECT, VERTEX_AI_LOCATION, and GARDEN_ENDPOINT_ID."
            )
        return f"projects/{project}/locations/{location}/endpoints/{endpoint_id}"

    raise ValueError(f"Unhandled LLM_PROVIDER: {provider}")

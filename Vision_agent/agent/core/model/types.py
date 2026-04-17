"""Model provider types for ADK.

LLM_PROVIDER selects how the model string is resolved:
- vertex_ai: Gemini/Vertex AI via model name (e.g. gemini-2.0-flash); set GOOGLE_GENAI_USE_VERTEXAI=TRUE.
- garden: Vertex AI Model Garden endpoint (full resource path).
"""

from enum import Enum


class ModelProvider(str, Enum):
    """Supported LLM providers for ADK agents."""

    VERTEX_AI = "vertex_ai"  # Vertex AI / Gemini by model name
    GARDEN = "garden"  # Vertex AI Model Garden endpoint (projects/.../locations/.../endpoints/...)

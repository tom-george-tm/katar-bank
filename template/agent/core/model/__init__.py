"""Model provider: resolve Vertex AI / Model Garden model from env for ADK agents."""

from agent.core.model.provider import get_model
from agent.core.model.types import ModelProvider

__all__ = ["ModelProvider", "get_model"]

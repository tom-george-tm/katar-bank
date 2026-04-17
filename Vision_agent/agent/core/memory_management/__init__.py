"""Memory management - ADK BaseMemoryService (long-term knowledge), configurable via env."""

from agent.core.memory_management.factory import get_memory_service
from agent.core.memory_management.types import MemoryBackend

__all__ = ["get_memory_service", "MemoryBackend"]

"""Memory service factory. Returns ADK BaseMemoryService based on MEMORY_SERVICE_BACKEND."""

from __future__ import annotations

from agent.core.config import settings
from agent.core.memory_management.connectors.inmemory import (
    create_inmemory_memory_service,
)
from agent.core.memory_management.connectors.redis import (
    create_redis_long_term_memory_service,
)
from agent.core.memory_management.types import MemoryBackend


def get_memory_service():
    """
    Return the configured ADK BaseMemoryService from env MEMORY_SERVICE_BACKEND, or None.

    Supported: none, inmemory, redis.
    Returns None when backend is "none" (Runner accepts memory_service=None).
    """
    raw = (settings.MEMORY_SERVICE_BACKEND or "inmemory").strip().lower()
    try:
        backend = MemoryBackend(raw)
    except ValueError:
        raise ValueError(
            f"Invalid MEMORY_SERVICE_BACKEND={raw!r}. "
            f"Must be one of: {', '.join(b.value for b in MemoryBackend)}"
        ) from None

    if backend is MemoryBackend.NONE:
        return None
    if backend is MemoryBackend.INMEMORY:
        return create_inmemory_memory_service()
    if backend is MemoryBackend.REDIS:
        return create_redis_long_term_memory_service()
    raise ValueError(f"Unhandled memory backend: {backend}")

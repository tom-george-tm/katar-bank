"""Memory service backend enum. Used by memory_management factory."""

from __future__ import annotations

from enum import Enum


class MemoryBackend(str, Enum):
    """Supported memory service backends. Set via MEMORY_SERVICE_BACKEND env."""

    NONE = "none"
    INMEMORY = "inmemory"
    REDIS = "redis"  # adk-redis: Redis Agent Memory Server (pip install adk-redis[memory])

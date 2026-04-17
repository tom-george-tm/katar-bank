"""Redis long-term memory – adk-redis RedisLongTermMemoryService (Redis Agent Memory Server).

Requires: pip install adk-redis[memory]
Backend: Redis Agent Memory Server (https://github.com/redis/agent-memory-server)
Docs: https://github.com/redis-developer/adk-redis
"""

from __future__ import annotations

from agent.core.config import settings


def create_redis_long_term_memory_service():
    """Return RedisLongTermMemoryService from adk-redis. Requires Agent Memory Server at REDIS_MEMORY_API_BASE_URL."""
    try:
        from adk_redis.memory import (
            RedisLongTermMemoryService,
            RedisLongTermMemoryServiceConfig,
        )
    except ImportError:
        raise ImportError(
            "Redis long-term memory requires adk-redis with memory extra. "
            "Install with: pip install adk-redis[memory]"
        ) from None

    api_base_url = (settings.REDIS_MEMORY_API_BASE_URL or "").strip()
    if not api_base_url:
        raise ValueError(
            "REDIS_MEMORY_API_BASE_URL must be set when MEMORY_SERVICE_BACKEND=redis "
            "(e.g. http://localhost:8088 for Redis Agent Memory Server)"
        )

    config = RedisLongTermMemoryServiceConfig(
        api_base_url=api_base_url,
        default_namespace=settings.REDIS_MEMORY_NAMESPACE or "adk_app",
        extraction_strategy=settings.REDIS_MEMORY_EXTRACTION_STRATEGY or "discrete",
        recency_boost=settings.REDIS_MEMORY_RECENCY_BOOST,
    )
    return RedisLongTermMemoryService(config=config)

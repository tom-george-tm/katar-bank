"""Redis / Memorystore session service.

Uses `google-adk-redis`'s RedisMemorySessionService to provide an ADK
BaseSessionService backed by Redis. This is suitable for local development
and lightweight production use.
"""

from __future__ import annotations

from agent.core.config import settings


def create_redis_session_service():
    """Create Redis-backed session service. Set SESSION_SERVICE_BACKEND=redis."""
    try:
        from google_adk_redis import RedisMemorySessionService
    except ImportError:
        raise ImportError(
            "Redis session service requires google-adk-redis. "
            "Install with: pip install google-adk-redis"
        ) from None

    return RedisMemorySessionService(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
    )


def create_memorystore_session_service():
    """Create Memorystore (Redis-compatible) session service. Set MEMORYSTORE_REDIS_URL or REDIS_URL."""
    try:
        from google.adk_community.sessions.redis_session_service import (
            RedisSessionService,
        )
    except ImportError:
        raise ImportError(
            "Redis session service requires google-adk-redis. "
            "Install with: pip install google-adk-redis"
        ) from None
    url = (settings.MEMORYSTORE_REDIS_URL or settings.REDIS_URL or "").strip()
    if not url:
        raise ValueError(
            "MEMORYSTORE_REDIS_URL or REDIS_URL must be set for memorystore backend"
        )
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or settings.REDIS_HOST or "localhost"
    port = parsed.port or settings.REDIS_PORT or 6379
    return RedisSessionService(host=host, port=port, db=0)

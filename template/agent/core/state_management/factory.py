"""Session service factory. Returns ADK BaseSessionService based on SESSION_SERVICE_BACKEND."""

from __future__ import annotations

from agent.core.config import settings
from agent.core.state_management.connectors.firestore import (
    create_firestore_session_service,
)
from agent.core.state_management.connectors.inmemory import (
    create_inmemory_session_service,
)
from agent.core.state_management.connectors.mongodb import (
    create_mongodb_session_service,
)
from agent.core.state_management.connectors.postgres import (
    create_postgres_session_service,
)
from agent.core.state_management.connectors.redis import (
    create_memorystore_session_service,
    create_redis_session_service,
)
from agent.core.state_management.types import SessionBackend


def get_session_service():
    """
    Return the configured ADK BaseSessionService from env SESSION_SERVICE_BACKEND.

    Supported: inmemory, firestore, redis, memorystore, postgres, mongodb.
    Set backend-specific env vars (e.g. FIRESTORE_PROJECT, FIRESTORE_DATABASE for firestore; REDIS_URL for redis).
    """
    raw = (settings.SESSION_SERVICE_BACKEND or "inmemory").strip().lower()
    try:
        backend = SessionBackend(raw)
    except ValueError:
        raise ValueError(
            f"Invalid SESSION_SERVICE_BACKEND={raw!r}. "
            f"Must be one of: {', '.join(b.value for b in SessionBackend)}"
        ) from None

    if backend is SessionBackend.INMEMORY:
        return create_inmemory_session_service()
    if backend is SessionBackend.FIRESTORE:
        project = (settings.FIRESTORE_PROJECT or "").strip()
        if not project:
            raise ValueError(
                "FIRESTORE_PROJECT must be set when SESSION_SERVICE_BACKEND=firestore"
            )
        return create_firestore_session_service(
            project=project,
            database=settings.FIRESTORE_DATABASE or "(default)",
        )
    if backend is SessionBackend.REDIS:
        return create_redis_session_service()
    if backend is SessionBackend.MEMORYSTORE:
        return create_memorystore_session_service()
    if backend is SessionBackend.POSTGRES:
        return create_postgres_session_service()
    if backend is SessionBackend.MONGODB:
        return create_mongodb_session_service()
    raise ValueError(f"Unhandled session backend: {backend}")

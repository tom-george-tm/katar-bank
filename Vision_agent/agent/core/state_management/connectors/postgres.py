"""Postgres session service backed by ADK's DatabaseSessionService."""

from __future__ import annotations

from agent.core.config import settings
from google.adk.sessions import DatabaseSessionService


def create_postgres_session_service():
    """Create Postgres-backed session service using ADK's database backend."""
    db_url = (settings.POSTGRES_URI or "").strip()
    if not db_url:
        raise ValueError(
            "POSTGRES_URI must be set when SESSION_SERVICE_BACKEND=postgres. "
            "Use an async SQLAlchemy URL such as "
            "`postgresql+asyncpg://user:password@localhost:5432/adk_sessions`."
        )
    if not db_url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            "POSTGRES_URI must use the asyncpg driver, for example "
            "`postgresql+asyncpg://user:password@localhost:5432/adk_sessions`."
        )
    return DatabaseSessionService(db_url=db_url)

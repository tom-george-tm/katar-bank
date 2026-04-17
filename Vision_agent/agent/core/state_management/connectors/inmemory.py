"""In-memory session service - ADK built-in. No persistence."""

from __future__ import annotations

from google.adk.sessions import InMemorySessionService


def create_inmemory_session_service():
    """Return ADK InMemorySessionService. Suitable for dev/test; data lost on restart."""
    return InMemorySessionService()

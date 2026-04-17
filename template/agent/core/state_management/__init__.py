"""State (session) management - ADK BaseSessionService, configurable via env."""

from agent.core.state_management.factory import get_session_service
from agent.core.state_management.types import SessionBackend

__all__ = ["get_session_service", "SessionBackend"]

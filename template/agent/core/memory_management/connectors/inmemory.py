"""In-memory memory service - ADK built-in. Long-term knowledge in process; no persistence."""

from __future__ import annotations

from google.adk.memory import InMemoryMemoryService


def create_inmemory_memory_service():
    """Return ADK InMemoryMemoryService. Keyword search; data lost on restart."""
    return InMemoryMemoryService()

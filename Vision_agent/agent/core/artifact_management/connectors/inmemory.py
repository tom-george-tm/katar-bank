"""In-memory artifact service - ADK built-in. No persistence; for dev/test."""

from __future__ import annotations

from google.adk.artifacts import InMemoryArtifactService


def create_inmemory_artifact_service():
    """Return ADK InMemoryArtifactService. Artifacts lost on restart."""
    return InMemoryArtifactService()

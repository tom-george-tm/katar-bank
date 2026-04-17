"""Artifact service factory. Returns ADK BaseArtifactService based on ARTIFACT_SERVICE_BACKEND."""

from __future__ import annotations

from agent.core.config import settings
from agent.core.artifact_management.connectors.gcs import create_gcs_artifact_service
from agent.core.artifact_management.connectors.inmemory import (
    create_inmemory_artifact_service,
)
from agent.core.artifact_management.types import ArtifactBackend


def get_artifact_service():
    """
    Return the configured ADK BaseArtifactService from env ARTIFACT_SERVICE_BACKEND, or None.

    Supported: none, inmemory, gcs.
    Returns None when backend is "none" (Runner accepts artifact_service=None).
    """
    raw = (settings.ARTIFACT_SERVICE_BACKEND or "inmemory").strip().lower()
    try:
        backend = ArtifactBackend(raw)
    except ValueError:
        raise ValueError(
            f"Invalid ARTIFACT_SERVICE_BACKEND={raw!r}. "
            f"Must be one of: {', '.join(b.value for b in ArtifactBackend)}"
        ) from None

    if backend is ArtifactBackend.NONE:
        return None
    if backend is ArtifactBackend.INMEMORY:
        return create_inmemory_artifact_service()
    if backend is ArtifactBackend.GCS:
        return create_gcs_artifact_service()
    raise ValueError(f"Unhandled artifact backend: {backend}")

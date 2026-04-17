"""Artifact management - ADK BaseArtifactService, configurable via env."""

from agent.core.artifact_management.factory import get_artifact_service
from agent.core.artifact_management.types import ArtifactBackend

__all__ = ["get_artifact_service", "ArtifactBackend"]

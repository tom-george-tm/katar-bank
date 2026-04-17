"""Artifact service backend enum. Used by artifact_management factory."""

from __future__ import annotations

from enum import Enum


class ArtifactBackend(str, Enum):
    """Supported artifact service backends. Set via ARTIFACT_SERVICE_BACKEND env."""

    NONE = "none"
    INMEMORY = "inmemory"
    GCS = "gcs"

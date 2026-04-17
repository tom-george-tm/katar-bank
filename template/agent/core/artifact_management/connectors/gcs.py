"""GCS artifact service - ADK built-in. Persistent artifact storage in Google Cloud Storage."""

from __future__ import annotations

from agent.core.config import settings
from google.adk.artifacts import GcsArtifactService

def create_gcs_artifact_service():
    """Return ADK GcsArtifactService. Set GCS_ARTIFACT_BUCKET and have GCS credentials."""

    bucket = (settings.GCS_ARTIFACT_BUCKET or "").strip()
    if not bucket:
        raise ValueError(
            "GCS_ARTIFACT_BUCKET must be set for ARTIFACT_SERVICE_BACKEND=gcs"
        )
    return GcsArtifactService(bucket_name=bucket)

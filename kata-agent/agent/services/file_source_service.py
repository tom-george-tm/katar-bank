from __future__ import annotations

import asyncio
import os

from fastapi import HTTPException


def parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    """Split gs://bucket/path URI into (bucket, object_path)."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError("gcs_uri must start with 'gs://'.")
    uri_without_prefix = gcs_uri[5:]
    if "/" not in uri_without_prefix:
        raise ValueError("gcs_uri must include an object path, e.g. gs://bucket/path/to/file.pdf.")
    bucket_name, object_path = uri_without_prefix.split("/", 1)
    if not bucket_name or not object_path:
        raise ValueError("gcs_uri must include both bucket and object path.")
    return bucket_name, object_path


async def download_gcs_file(gcs_uri: str) -> tuple[bytes, str]:
    """Download a file from GCS and return (content_bytes, filename)."""
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="google-cloud-storage dependency is not installed.",
        ) from exc

    credentials_path = os.getenv("CREDENTIALS_PATH")
    if not credentials_path:
        raise HTTPException(
            status_code=500,
            detail="CREDENTIALS_PATH env var is required to read from GCS.",
        )

    try:
        bucket_name, object_path = parse_gcs_uri(gcs_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    client = storage.Client(credentials=credentials)

    blob = client.bucket(bucket_name).blob(object_path)
    exists = await asyncio.to_thread(blob.exists)
    if not exists:
        raise HTTPException(status_code=404, detail=f"GCS object not found: {gcs_uri}")

    file_content = await asyncio.to_thread(blob.download_as_bytes)
    if not file_content:
        raise HTTPException(status_code=400, detail="GCS object content is empty.")

    filename = object_path.rsplit("/", 1)[-1] or "document"
    return file_content, filename

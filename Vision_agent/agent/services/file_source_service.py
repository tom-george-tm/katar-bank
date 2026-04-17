from __future__ import annotations

import asyncio
from agent.core.config import settings
from agent.exceptions.base import ToolConfigurationException, APIException

def parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    """Split gs://bucket/path URI into (bucket, object_path)."""
    if not gcs_uri.startswith("gs://"):
        raise APIException("gcs_uri must start with 'gs://'.", status_code=400)
    uri_without_prefix = gcs_uri[5:]
    if "/" not in uri_without_prefix:
        raise APIException("gcs_uri must include an object path, e.g. gs://bucket/path/to/file.pdf.", status_code=400)
    bucket_name, object_path = uri_without_prefix.split("/", 1)
    if not bucket_name or not object_path:
        raise APIException("gcs_uri must include both bucket and object path.", status_code=400)
    return bucket_name, object_path


async def download_gcs_file(gcs_uri: str) -> tuple[bytes, str]:
    """Download a file from GCS and return (content_bytes, filename)."""
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
    except ImportError as exc:
        raise ToolConfigurationException(
            "google-cloud-storage dependency is not installed."
        ) from exc

    credentials_path = settings.CREDENTIALS_PATH
    if not credentials_path:
        raise ToolConfigurationException(
            "CREDENTIALS_PATH is not configured in settings."
        )

    try:
        bucket_name, object_path = parse_gcs_uri(gcs_uri)
    except APIException:
        raise
    except Exception as exc:
        raise APIException(str(exc), status_code=400) from exc

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        client = storage.Client(credentials=credentials)

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_path)
        
        exists = await asyncio.to_thread(blob.exists)
        if not exists:
            raise APIException(f"GCS object not found: {gcs_uri}", status_code=404)

        file_content = await asyncio.to_thread(blob.download_as_bytes)
        if not file_content:
            raise APIException("GCS object content is empty.", status_code=400)

        filename = object_path.rsplit("/", 1)[-1] or "document"
        return file_content, filename
    except APIException:
        raise
    except Exception as exc:
        raise APIException(f"Failed to download from GCS: {exc}", status_code=500) from exc

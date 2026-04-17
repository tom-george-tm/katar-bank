import asyncio

from agent.services.file_source_service import download_gcs_file
from agent.state import ACTIVE_FILE_CONTENT, ACTIVE_MIME_TYPE

def download_gcs_tool(gcs_uri: str) -> dict:
    """
    Downloads a document from a Google Cloud Storage URI.
    
    Args:
        gcs_uri: The full GCS path (e.g., gs://my-bucket/doc.pdf)
        
    Returns:
        A dictionary containing the metadata. The document bytes are stored 
        internally for use by subsequent OCR and Vision tools.
    """
    content, filename = asyncio.run(download_gcs_file(gcs_uri))
    
    # Store the downloaded content in the session context
    ACTIVE_FILE_CONTENT.set(content)
    # Note: mime_type might need to be detected later if not obvious from extension
    
    return {
        "file_content_len": len(content),
        "original_filename": filename,
        "status": "successfully_downloaded_and_stored_in_context"
    }
from agent.services.preprocessing_service import preprocess_for_ocr
from agent.state import ACTIVE_FILE_CONTENT, ACTIVE_MIME_TYPE
from agent.exceptions.base import APIException

def preprocess_tool(file_content: bytes = None, mime_type: str = None) -> dict:
    """
    Cleans and optimizes a document for better OCR accuracy. 
    Performs deskewing, gamma correction, and PDF-to-Image conversion if needed.
    
    Args:
        file_content: Raw bytes of the document. If omitted, uses the current document in context.
        mime_type: The MIME type of the file.
        
    Returns:
        A dictionary containing the processed bytes and metadata.
        NOTE: This tool updates the internal document state, so subsequent OCR tools 
        will automatically use the cleaned version.
    """
    content = file_content or ACTIVE_FILE_CONTENT.get()
    m_type = mime_type or ACTIVE_MIME_TYPE.get()
    
    if not content:
        raise APIException("No file content available for preprocessing.", status_code=400)

    processed_bytes, out_mime, metadata = preprocess_for_ocr(content, m_type)
    
    # Update the global context state so the next tool uses the optimized version
    ACTIVE_FILE_CONTENT.set(processed_bytes)
    ACTIVE_MIME_TYPE.set(out_mime)
    
    return {
        "ocr_file_content_len": len(processed_bytes),
        "ocr_mime_type": out_mime,
        "preprocessing_metadata": metadata
    }
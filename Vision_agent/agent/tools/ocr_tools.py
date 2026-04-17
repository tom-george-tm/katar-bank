import asyncio
from agent.services.docai_service import process_document
from agent.state import ACTIVE_FILE_CONTENT, ACTIVE_MIME_TYPE
from agent.exceptions.base import APIException

def document_ocr_tool(processor_type: str = "document_ocr", include_word_confidence: bool = False, file_content: bytes = None, mime_type: str = None):
    """
    Executes Google Document AI OCR. Useful for extracting tables, forms, and raw text from documents.
    
    Args:
        processor_type: The type of processor to use ('document_ocr', 'form_parser', 'layout_parser').
        include_word_confidence: Whether to include confidence scores for each word.
        file_content: Optional bytes of the document. If omitted, uses the current document in context.
        mime_type: Optional MIME type of the file.
    """
    content = file_content or ACTIVE_FILE_CONTENT.get()
    m_type = mime_type or ACTIVE_MIME_TYPE.get()
    
    if not content:
        raise APIException("No file content available for OCR. Provide file_content or ensure a file is loaded.", status_code=400)

    # Using asyncio.run to call the async service from the synchronous tool interface
    ocr_result, _ = asyncio.run(process_document(
        file_content=content,
        processor_type=processor_type,
        include_word_confidence=include_word_confidence,
        mime_type=m_type
    ))
    return ocr_result
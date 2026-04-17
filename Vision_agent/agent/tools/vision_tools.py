import asyncio

from agent.services.vertex_service import analyze_document
from agent.state import ACTIVE_FILE_CONTENT, ACTIVE_MIME_TYPE

def gemini_vision_tool(prompt: str, file_content: bytes = None, mime_type: str = None, extraction_schema: dict = None):
    """
    Uses Gemini Vision for high-level reasoning or structured JSON extraction.
    
    Args:
        prompt: The text prompt or instructions for Gemini.
        file_content: Optional bytes of the document/image. If omitted, uses the current document in context.
        mime_type: Optional MIME type of the file.
        extraction_schema: Optional JSON schema for structured extraction.
    """
    content = file_content or ACTIVE_FILE_CONTENT.get()
    m_type = mime_type or ACTIVE_MIME_TYPE.get()

    result = asyncio.run(analyze_document(
        prompt=prompt,
        file_content=content,
        mime_type=m_type,
        extraction_schema=extraction_schema
    ))
    return result
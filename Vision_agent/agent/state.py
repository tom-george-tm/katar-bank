import contextvars
from typing import Optional

# Context variable to hold the binary content of the document being processed.
# This allows tools to access the document bytes without the Agent having to
# pass large byte strings back and forth through the LLM context.
ACTIVE_FILE_CONTENT: contextvars.ContextVar[Optional[bytes]] = contextvars.ContextVar("active_file_content", default=None)
ACTIVE_MIME_TYPE: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("active_mime_type", default=None)

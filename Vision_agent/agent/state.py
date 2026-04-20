import contextvars
from typing import Optional

ACTIVE_FILE_CONTENT: contextvars.ContextVar[Optional[bytes]] = contextvars.ContextVar("active_file_content", default=None)
ACTIVE_MIME_TYPE: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("active_mime_type", default=None)

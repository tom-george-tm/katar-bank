from __future__ import annotations

import logging
from agent.schemas.state import VisionState
from agent.services.preprocessing_service import preprocess_for_ocr

logger = logging.getLogger(__name__)


async def prepare_ocr_input_node(state: VisionState) -> dict:
    """Preprocess the uploaded file for OCR and store the preprocessed bytes and metadata in state."""

    mime_type = state.get("mime_type")
    if not mime_type:
        raise ValueError("mime_type must be set before OCR preprocessing.")
    logger.info(
        "Starting OCR preprocessing",
        extra={"mime_type": mime_type},
    )

    ocr_file_content, ocr_mime_type, preprocessing_metadata = preprocess_for_ocr(
        state["file_content"],
        mime_type,
    )
    logger.info(
        "Finished OCR preprocessing",
        extra={
            "mime_type": mime_type,
            "ocr_mime_type": ocr_mime_type,
        },
    )
    return {
        "ocr_file_content": ocr_file_content,
        "ocr_mime_type": ocr_mime_type,
        "ocr_preprocessing_metadata": preprocessing_metadata,
    }

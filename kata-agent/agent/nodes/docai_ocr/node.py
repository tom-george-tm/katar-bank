from __future__ import annotations

import logging
from agent.schemas.state import VisionState, FlowType, ProcessorType
from agent.services.docai_service import process_document

logger = logging.getLogger(__name__)


async def docai_ocr_node(state: VisionState) -> dict:
    """Call Document AI to run OCR on the (possibly preprocessed) document and attach OCR results to state."""

    processor_type = state.get("processor_type") or ProcessorType.DOCUMENT_OCR
    include_word_confidence = state.get("include_word_confidence", False)
    file_content = state.get("ocr_file_content") or state["file_content"]
    ocr_mime_type = state.get("ocr_mime_type")

    logger.info(
        "Starting OCR (Document AI)",
        extra={
            "processor_type": processor_type.value,
            "include_word_confidence": include_word_confidence,
            "mime_type": ocr_mime_type,
        },
    )

    ocr_result, docai_document = await process_document(
        file_content,
        processor_type.value,
        include_word_confidence=include_word_confidence,
        mime_type=ocr_mime_type,
    )

    logger.info(
        "Finished OCR (Document AI)",
        extra={
            "processor_type": processor_type.value,
            "include_word_confidence": include_word_confidence,
            "mime_type": ocr_mime_type,
        },
    )

    ocr_result["preprocessing_metadata"] = state.get("ocr_preprocessing_metadata", {})
    return {
        "ocr_result": ocr_result,
        "ocr_text": ocr_result.get("text", ""),
        "docai_document": docai_document,
    }


def route_after_ocr(state: VisionState) -> str:
    """Choose the next step after OCR has completed, based on the configured flow."""
    flow_type = state.get("flow_type")
    if flow_type == FlowType.OCR_PIPELINE:
        return "ocr_pipeline"
    if flow_type == FlowType.OCR_VISION_PIPELINE:
        return "ocr_vision_pipeline"
    raise ValueError(f"Unexpected flow after OCR: {flow_type}")

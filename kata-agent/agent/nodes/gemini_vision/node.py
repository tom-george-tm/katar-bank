from __future__ import annotations

import logging
from agent.schemas.state import VisionState, FlowType
from agent.llm_models.vertex_ai import analyze_document

logger = logging.getLogger(__name__)


async def gemini_vision_node(state: VisionState) -> dict:
    """Send the pipeline prompt (and optionally the original file) to Gemini Vision and store the LLM output in state."""

    prompt = state.get("pipeline_prompt") or ""
    include_image = state.get("include_image_in_vision", True)

    logger.info(
        "Starting Gemini vision call",
        extra={
            "include_image": include_image,
            "has_extraction_schema": bool(state.get("extraction_schema")),
        },
    )

    if include_image:
        mime_type = state.get("mime_type")
        if not mime_type:
            raise ValueError("mime_type must be set before calling Gemini with image content.")

        vision_result = await analyze_document(
            prompt=prompt,
            file_content=state["file_content"],
            mime_type=mime_type,
            extraction_schema=state.get("extraction_schema"),
        )
    else:
        vision_result = await analyze_document(
            prompt=prompt,
            extraction_schema=state.get("extraction_schema"),
        )

    logger.info(
        "Finished Gemini vision call",
        extra={
            "include_image": include_image,
            "has_extraction_schema": bool(state.get("extraction_schema")),
        },
    )
    return {"vision_result": vision_result}


def route_after_vision(state: VisionState) -> str:
    """Choose the finalization path after the Gemini vision step based on the configured flow."""
    flow_type = state.get("flow_type")
    if flow_type == FlowType.VISION_PIPELINE:
        return "vision_pipeline"
    if flow_type == FlowType.OCR_VISION_PIPELINE:
        return "ocr_vision_pipeline"
    raise ValueError(f"Unexpected flow after vision: {flow_type}")

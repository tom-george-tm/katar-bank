from __future__ import annotations

import logging
from agent.schemas.state import VisionState
from agent.nodes.build_pipeline_prompt.helper.formatters import format_ocr_as_markdown
from agent.nodes.build_pipeline_prompt.prompt import build_ocr_vision_prompt

logger = logging.getLogger(__name__)


def has_arabic_language(languages: list[str]) -> bool:
    return any(language.split("-")[0] == "ar" for language in languages)


async def build_pipeline_prompt_node(state: VisionState) -> dict:
    """Convert OCR results into markdown and build the combined OCR+vision pipeline prompt."""
    ocr_result = state.get("ocr_result") or {}
    logger.info(
        "Building OCR+vision pipeline prompt",
        extra={
            "has_ocr_result": bool(ocr_result),
            "has_custom_prompt": bool(state.get("custom_prompt")),
            "has_extraction_schema": bool(state.get("extraction_schema")),
        },
    )

    ocr_markdown = format_ocr_as_markdown(ocr_result)
    has_extraction_schema = bool(state.get("extraction_schema"))
    processor_metadata = ocr_result.get("processor_metadata") or {}
    languages = processor_metadata.get("languages") or []
    use_arabic_structured_prompt = has_extraction_schema and has_arabic_language(languages)

    pipeline_prompt = build_ocr_vision_prompt(
        ocr_markdown,
        state.get("custom_prompt"),
        has_extraction_schema=has_extraction_schema,
        has_arabic_language=use_arabic_structured_prompt,
    )
    return {
        "ocr_markdown_text": ocr_markdown,
        "pipeline_prompt": pipeline_prompt,
    }

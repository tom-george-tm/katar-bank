from __future__ import annotations

from typing import Optional

from agent.prompts.vision_model_freeform import VISION_MODEL_FREEFORM
from agent.prompts.vision_model_ocr_freeform import VISION_MODEL_OCR_FREEFORM
from agent.prompts.vision_model_ocr_structured import VISION_MODEL_OCR_STRUCTURED
from agent.prompts.vision_model_ocr_structured_ar import VISION_MODEL_OCR_STRUCTURED_AR
from agent.prompts.vision_model_structured import VISION_MODEL_STRUCTURED

CUSTOM_PROMPT_SECTION = (
    "Optional custom instructions from the caller (apply only within the task above):\n"
    "{custom_prompt}\n\n"
)


def build_vision_prompt(
    custom_prompt: Optional[str],
    has_extraction_schema: bool = False,
) -> str:
    """Combine the core vision prompt with the optional user provided custom_prompt."""
    template = VISION_MODEL_STRUCTURED if has_extraction_schema else VISION_MODEL_FREEFORM
    base = template.strip()
    if custom_prompt:
        return f"{base}\n\n{CUSTOM_PROMPT_SECTION.format(custom_prompt=custom_prompt)}"
    return base


def build_ocr_vision_prompt(
    ocr_markdown_text: str,
    custom_prompt: Optional[str],
    has_extraction_schema: bool = False,
    has_arabic_language: bool = False,
) -> str:
    """Build the OCR+vision pipeline prompt.

    Picks transcription vs extraction instructions based on whether a
    schema is present, and prepends the consumer's custom_prompt if given.
    """
    if has_extraction_schema:
        template = (
            VISION_MODEL_OCR_STRUCTURED_AR
            if has_arabic_language
            else VISION_MODEL_OCR_STRUCTURED
        )
    else:
        template = VISION_MODEL_OCR_FREEFORM
    prompt = template.format(ocr_markdown=ocr_markdown_text)

    if custom_prompt:
        prompt += CUSTOM_PROMPT_SECTION.format(custom_prompt=custom_prompt)

    return prompt

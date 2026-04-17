from agent.utils.prompt_build import build_ocr_vision_prompt, build_vision_prompt
from agent.utils.formatters import format_ocr_as_markdown
from typing import Optional

def has_arabic_language(languages: list[str]) -> bool:
    """Detects if Arabic is present in the list of languages."""
    return any(language.split("-")[0] == "ar" for language in languages)

def get_vision_instructions_tool(
    ocr_result: Optional[dict] = None,
    custom_prompt: Optional[str] = None,
    has_extraction_schema: bool = False,
    flow_type: str = "vision_pipeline"
) -> str:
    """
    Constructs the specialized system instructions for the Gemini Vision model 
    based on whether OCR data is present, the language detected, and the flow type.
    
    Args:
        ocr_result: The raw JSON output from the Document AI OCR tool. Required for 'ocr_vision_pipeline'.
        custom_prompt: Optional user-provided custom requirements to append to the instructions.
        has_extraction_schema: Set to True if the goal is structured extraction into a JSON schema.
        flow_type: The pipeline flow ('vision_pipeline' for image-only or 'ocr_vision_pipeline' for hybrid).
    """
    if flow_type == "ocr_vision_pipeline" and ocr_result:
        # Convert OCR JSON to Markdown for LLM consumption
        ocr_markdown = format_ocr_as_markdown(ocr_result)
        
        # Check for Arabic to use the specialized Arabic extraction prompt
        processor_metadata = ocr_result.get("processor_metadata") or {}
        languages = processor_metadata.get("languages") or []
        use_arabic_prompt = has_extraction_schema and has_arabic_language(languages)

        return build_ocr_vision_prompt(
            ocr_markdown_text=ocr_markdown,
            custom_prompt=custom_prompt,
            has_extraction_schema=has_extraction_schema,
            has_arabic_language=use_arabic_prompt
        )
    else:
        # Defaults or pure vision flow
        return build_vision_prompt(
            custom_prompt=custom_prompt,
            has_extraction_schema=has_extraction_schema
        )

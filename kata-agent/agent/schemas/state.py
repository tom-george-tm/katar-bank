from __future__ import annotations

from enum import Enum
from typing import Any, Optional, TypedDict


class FlowType(str, Enum):
    """High-level document pipeline to run. Single source of truth for API and graph."""

    OCR_PIPELINE = "ocr_pipeline"
    VISION_PIPELINE = "vision_pipeline"
    OCR_VISION_PIPELINE = "ocr_vision_pipeline"


class ProcessorType(str, Enum):
    """Document AI processor used for OCR. Single source of truth for API and graph."""

    FORM_PARSER = "form_parser"
    DOCUMENT_OCR = "document_ocr"
    LAYOUT_PARSER = "layout_parser"


class VisionState(TypedDict, total=False):
    file_content: bytes
    original_filename: str
    mime_type: str
    # Controls whether the original file/image is sent to the vision model,
    # or whether we run the LLM in text-only mode with just the prompt.
    include_image_in_vision: bool
    ocr_file_content: bytes
    ocr_mime_type: str
    ocr_preprocessing_metadata: dict
    flow_type: Optional[FlowType]
    processor_type: Optional[ProcessorType]
    include_word_confidence: bool

    # custom_prompt = prompt supplied by API consumer
    custom_prompt: Optional[str]
    pipeline_prompt: Optional[str]

    # JSON schema for structured extraction (Gemini response_schema)
    extraction_schema: Optional[dict]

    ocr_result: Optional[dict]
    ocr_text: Optional[str]
    ocr_markdown_text: Optional[str]
    vision_result: Optional[dict]

    # Raw Document AI protobuf; kept in-process only for geometry correction, never serialized to response.
    docai_document: Optional[Any]

    final_output: Optional[dict]

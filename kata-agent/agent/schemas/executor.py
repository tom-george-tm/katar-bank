from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent.schemas.state import FlowType, ProcessorType


class AgentInput(BaseModel):
    """Schema for document processing request payloads."""
    flow_type: FlowType = Field(..., description="Pipeline flow to execute.")
    processor_type: Optional[ProcessorType] = Field(
        None,
        description="Document AI processor used for OCR. Required for OCR flows.",
    )
    custom_prompt: Optional[str] = Field(
        None,
        description="Optional prompt sent to the vision model (vision flows only).",
    )
    include_word_confidence: bool = Field(
        False,
        description="If true, include word-level confidence in OCR output (OCR flows only).",
    )
    extraction_schema: Optional[dict[str, Any]] = Field(
        None,
        description="JSON schema for structured extraction (Gemini response_schema).",
    )
    include_image_in_vision: bool = Field(
        False,
        description=(
            "If true, the vision step receives the original image alongside the OCR text. "
            "Only supported for ocr_vision_pipeline."
        ),
    )
    gcs_uri: Optional[str] = Field(
        None,
        description="GCS object URI (gs://bucket/path/file). Provide if no file is attached.",
    )


class InputInfo(BaseModel):
    """Metadata about the processed input."""
    processor_type: Optional[str] = Field(None, description="Document AI processor used for OCR")
    mime_type: str = Field(..., description="Detected MIME type of the document")
    custom_prompt: Optional[str] = Field(None, description="Prompt sent to the vision model")


class ResultInfo(BaseModel):
    """The results of the document processing pipeline."""
    ocr: Optional[dict[str, Any]] = Field(None, description="Document AI OCR output (text, data structures, etc.)")
    vision: Optional[dict[str, Any]] = Field(None, description="Gemini vision output (text or structured JSON)")


class ProcessResponse(BaseModel):
    """Final response body returned by the Vision Agent service."""
    flow: str = Field(..., description="Pipeline flow that was executed")
    input: InputInfo
    result: ResultInfo

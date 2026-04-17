from typing import Any, Optional
from pydantic import BaseModel, Field

class InputSchemaModel(BaseModel):
    """Input contract for the Vision Agent."""
    processor_type: Optional[str] = Field(None, description="Document AI processor type (e.g., document_ocr)")
    mime_type: Optional[str] = Field(None, description="Detected MIME type of the document")
    custom_prompt: Optional[str] = Field(None, description="Optional custom instructions for the vision model")
    gcs_uri: Optional[str] = Field(None, description="GCS path (gs://...) to the document")
    flow_type: Optional[str] = Field(None, description="Target pipeline: ocr_pipeline, vision_pipeline, or ocr_vision_pipeline")
    extraction_schema: Optional[dict[str, Any]] = Field(None, description="JSON schema for structured extraction")
    include_word_confidence: bool = Field(False, description="Whether to include OCR word confidence")
    include_image_in_vision: bool = Field(True, description="Whether to send image bytes to the vision model")

class OutputSchemaModel(BaseModel):
    """Output contract for the Vision Agent."""
    flow: str = Field(..., description="The pipeline flow that was executed")
    ocr: Optional[dict[str, Any]] = Field(None, description="Extracted OCR results")
    vision: Optional[dict[str, Any]] = Field(None, description="Vision reasoning/transcription results")
    status: str = Field("SUCCESS", description="Execution status")
    error: Optional[str] = Field(None, description="Error message if status is FAILURE")

def get_input_schema_model():
    return InputSchemaModel

def get_output_schema_model():
    return OutputSchemaModel

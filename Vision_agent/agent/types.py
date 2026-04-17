from enum import Enum

class FlowType(str, Enum):
    """High-level document pipeline to run."""
    OCR_PIPELINE = "ocr_pipeline"
    VISION_PIPELINE = "vision_pipeline"
    OCR_VISION_PIPELINE = "ocr_vision_pipeline"

class ProcessorType(str, Enum):
    """Document AI processor used for OCR."""
    FORM_PARSER = "form_parser"
    DOCUMENT_OCR = "document_ocr"
    LAYOUT_PARSER = "layout_parser"

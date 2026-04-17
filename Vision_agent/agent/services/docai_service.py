import asyncio
from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account

from agent.core.config import settings
from agent.exceptions.base import ToolConfigurationException, APIException
from agent.utils.docai import (
    extract_entities,
    extract_form_fields,
    extract_image_quality,
    extract_languages,
    extract_tables,
    extract_word_confidence,
)


PROCESSOR_ENV_MAP = {
    "form_parser": "DOCAI_FORM_PARSER_ID",
    "document_ocr": "DOCAI_DOCUMENT_OCR_ID",
    "layout_parser": "DOCAI_LAYOUT_PARSER_ID",
}

MIME_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"BM": "image/bmp",
    b"II\x2a\x00": "image/tiff",
    b"MM\x00\x2a": "image/tiff",
    b"RIFF": "image/webp",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument",
}

PROJECT_ID = settings.GOOGLE_CLOUD_PROJECT
LOCATION = settings.DOCAI_LOCATION
CREDS_PATH = settings.CREDENTIALS_PATH

if not PROJECT_ID:
    raise ToolConfigurationException("GOOGLE_CLOUD_PROJECT is required in settings.")

if not LOCATION:
    raise ToolConfigurationException("DOCAI_LOCATION is required in settings.")

if not CREDS_PATH:
    raise ToolConfigurationException("CREDENTIALS_PATH is required in settings.")

try:
    CREDENTIALS = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
except Exception as e:
    raise ToolConfigurationException(f"Failed to load credentials from {CREDS_PATH}: {e}")

CLIENT_OPTIONS = ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
DOCUMENT_AI_CLIENT = documentai.DocumentProcessorServiceClient(
    client_options=CLIENT_OPTIONS,
    credentials=CREDENTIALS,
)

def detect_mime_type(content: bytes) -> str:
    """Infer the MIME type of a file from its magic bytes and basic content sniffing."""
    for signature, mime in MIME_SIGNATURES.items():
        if content[: len(signature)] == signature:
            if mime == "image/webp" and content[8:12] != b"WEBP":
                continue
            if mime == "application/vnd.openxmlformats-officedocument":
                if b"word/" in content[:2000]:
                    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if b"xl/" in content[:2000]:
                    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if b"ppt/" in content[:2000]:
                    return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                return mime
            return mime
    raise APIException(
        "Could not detect file type. Supported formats: PDF, PNG, JPEG, GIF, TIFF, BMP, WebP, DOCX, XLSX, PPTX.",
        status_code=400
    )


async def process_document(
    file_content: bytes,
    processor_type: str = "document_ocr",
    include_word_confidence: bool = False,
    mime_type: str | None = None,
) -> tuple[dict, documentai.Document]:
    """Call the configured Document AI processor and return findings."""
    
    # Map the processor type to the correct attribute in settings
    processor_key = PROCESSOR_ENV_MAP.get(processor_type)
    if not processor_key:
        raise APIException(f"Unknown processor type: {processor_type}", status_code=400)

    processor_id = getattr(settings, processor_key, None)
    if not processor_id:
        raise ToolConfigurationException(f"Processor ID not configured for {processor_type} (check {processor_key} in settings).")

    if mime_type is None:
        mime_type = detect_mime_type(file_content)

    resource_name = DOCUMENT_AI_CLIENT.processor_path(
        PROJECT_ID,
        LOCATION,
        processor_id,
    )

    raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)
    request_kwargs = {
        "name": resource_name,
        "raw_document": raw_document,
    }
    if processor_type != "layout_parser":
        request_kwargs["process_options"] = documentai.ProcessOptions(
            ocr_config=documentai.OcrConfig(enable_image_quality_scores=True)
        )
    request = documentai.ProcessRequest(**request_kwargs)

    try:
        result = await asyncio.to_thread(
            DOCUMENT_AI_CLIENT.process_document,
            request=request,
        )
    except Exception as e:
        raise APIException(f"Document AI processing failed: {e}", status_code=500)

    ocr_dict = format_response(result.document, processor_type, include_word_confidence)
    return ocr_dict, result.document


def format_response(
    document: documentai.Document,
    processor_type: str,
    include_word_confidence: bool,
) -> dict:
    """Convert a raw Document AI `Document` into the simplified response schema."""
    languages = extract_languages(document)
    image_quality = extract_image_quality(document)

    base = {
        "text": document.text,
        "entities": extract_entities(document),
        "form_fields": extract_form_fields(document),
        "tables": extract_tables(document),
        "processor_metadata": {
            "type": processor_type,
            "page_count": len(document.pages),
            "languages": languages,
        },
    }

    if image_quality:
        base["image_quality"] = image_quality

    if include_word_confidence:
        base["word_confidence"] = extract_word_confidence(document)

    return base

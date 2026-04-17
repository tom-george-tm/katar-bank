import asyncio
import os

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account
from utils.docai_utils import (
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

# DOCAI_LOCATION uses regional codes (e.g. "eu", "us"); Vertex uses full region names (e.g. "europe-west2").
# They are intentionally different — do not reuse the same env var for both.
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("DOCAI_LOCATION")
CREDS_PATH = os.getenv("CREDENTIALS_PATH")

if not PROJECT_ID:
    raise RuntimeError(
        "GCP_PROJECT_ID env var is required. "
        "Set it in your environment or .env file."
    )

if not LOCATION:
    raise RuntimeError(
        "DOCAI_LOCATION env var is required (e.g. 'eu'). "
        "Set it in your environment or .env file."
    )

if not CREDS_PATH:
    raise RuntimeError(
        "CREDENTIALS_PATH env var is required. "
        "Set it to the path of your service-account JSON key "
        "in your environment or .env file."
    )
CREDENTIALS = service_account.Credentials.from_service_account_file(
    CREDS_PATH, scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

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
    raise ValueError(
        "Could not detect file type. Supported formats: PDF, PNG, JPEG, GIF, TIFF, BMP, WebP, DOCX, XLSX, PPTX."
    )


async def process_document(
    file_content: bytes,
    processor_type: str = "document_ocr",
    include_word_confidence: bool = False,
    mime_type: str | None = None,
) -> tuple[dict, documentai.Document]:
    """Call the configured Document AI processor and return the normalized dict plus raw Document.

    The raw Document is returned so downstream steps (e.g. geometry-based
    field correction) can access token-level bounding boxes without a second
    API call. It is never serialized into the HTTP response.

    When mime_type is provided (e.g. from preprocessing), it is used instead of detecting
    from file content, so the type matches what was actually sent to OCR.
    """
    env_key = PROCESSOR_ENV_MAP.get(processor_type)
    if not env_key:
        raise ValueError(f"Unknown processor type: {processor_type}")

    processor_id = os.getenv(env_key)
    if not processor_id:
        raise ValueError(
            f"Processor ID not configured. Set the {env_key} environment variable."
        )

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

    result = await asyncio.to_thread(
        DOCUMENT_AI_CLIENT.process_document,
        request=request,
    )

    ocr_dict = format_response(result.document, processor_type, include_word_confidence)
    return ocr_dict, result.document


def format_response(
    document: documentai.Document,
    processor_type: str,
    include_word_confidence: bool,
) -> dict:
    """Convert a raw Document AI `Document` into the simplified response schema used by this service."""
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

import json
import logging
from typing import Optional

from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from google.oauth2 import service_account

from agent.core.config import settings
from agent.utils.vertex_ai_utils import normalize_structured_vision_output

logger = logging.getLogger(__name__)

# Map settings to local constants for execution logic
PROJECT_ID = settings.GOOGLE_CLOUD_PROJECT
LOCATION = settings.VERTEX_AI_LOCATION
MODEL_NAME = settings.LLM_MODEL
MAX_OUTPUT_TOKENS = settings.GEMINI_MAX_OUTPUT_TOKENS
CREDS_PATH = settings.CREDENTIALS_PATH

# Service Account Credentials initialization - handle both service account and authorized user types
import json
try:
    with open(CREDS_PATH) as f:
        creds_info = json.load(f)
    
    if creds_info.get("type") == "service_account":
        CREDENTIALS = service_account.Credentials.from_service_account_file(
            CREDS_PATH, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    else:
        # For authorized_user or other types, use default credentials
        from google.auth import default
        CREDENTIALS, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
except Exception as e:
    print(f"Warning: Could not load credentials from {CREDS_PATH}: {e}")
    # Fall back to Application Default Credentials
    from google.auth import default
    CREDENTIALS, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

# Gemini Client initialization
CLIENT = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    credentials=CREDENTIALS,
    http_options=HttpOptions(api_version="v1"),
)


async def analyze_document(
    *,
    prompt: str,
    file_content: Optional[bytes] = None,
    mime_type: Optional[str] = None,
    extraction_schema: Optional[dict] = None,
) -> dict:
    """Call Gemini on the prompt and, optionally, the uploaded document.

    When *file_content* and *mime_type* are provided, the model receives both the
    document bytes and the prompt (multimodal mode). When they are omitted, the
    model is called in text-only mode with just the prompt.

    When *extraction_schema* is provided the model is constrained to return
    JSON that conforms to that schema (via Gemini's response_schema feature).
    """
    contents: list[types.Part | str] = [prompt]
    if file_content is not None:
        if not mime_type:
            raise ValueError("mime_type must be provided when file_content is supplied.")
        logger.info(
            "Gemini multimodal enabled: attaching document bytes",
            extra={
                "mime_type": mime_type,
                "file_content_bytes": len(file_content),
            },
        )
        document_part = types.Part.from_bytes(data=file_content, mime_type=mime_type)
        contents = [document_part, prompt]

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=MAX_OUTPUT_TOKENS
    )

    if extraction_schema:
        config.response_mime_type = "application/json"
        config.response_schema = extraction_schema

    response = await CLIENT.aio.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=config,
    )

    if extraction_schema:
        raw = response.text
        if raw is None:
            raise ValueError(
                "Vision model returned no text (empty or blocked). "
                "Check response.prompt_feedback for block reason if available."
            )
        try:
            structured_output = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Vision model returned invalid JSON for structured extraction: {e}. "
                "Raw response may be truncated or malformed."
            ) from e
        return normalize_structured_vision_output(structured_output)

    # Freeform text: ensure we never return text: null (use "" and optionally surface block reason)
    text = response.text if response.text is not None else ""
    out = {"text": text}
    if text == "" and getattr(response, "prompt_feedback", None) is not None:
        feedback = response.prompt_feedback
        if getattr(feedback, "block_reason", None) is not None:
            reason = str(feedback.block_reason)
            out["block_reason"] = reason
            logger.warning("Vision response blocked: block_reason=%s", reason)
    return out

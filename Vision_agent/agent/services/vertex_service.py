import json
import logging
from typing import Optional

from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from google.oauth2 import service_account

from agent.core.config import settings
from agent.exceptions.base import ToolConfigurationException, APIException
from agent.utils.vertex_ai_utils import normalize_structured_vision_output

logger = logging.getLogger(__name__)

# Config from central settings
PROJECT_ID = settings.GOOGLE_CLOUD_PROJECT
LOCATION = settings.VERTEX_AI_LOCATION
MODEL_NAME = settings.LLM_MODEL
MAX_OUTPUT_TOKENS = settings.GEMINI_MAX_OUTPUT_TOKENS
CREDS_PATH = settings.CREDENTIALS_PATH

if not PROJECT_ID:
    raise ToolConfigurationException("GOOGLE_CLOUD_PROJECT is required in settings.")

if not LOCATION:
    raise ToolConfigurationException("VERTEX_AI_LOCATION is required in settings.")

if not MODEL_NAME:
    raise ToolConfigurationException("LLM_MODEL is required in settings.")

if not CREDS_PATH:
    raise ToolConfigurationException("CREDENTIALS_PATH is required in settings.")

try:
    CREDENTIALS = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
except Exception as e:
    raise ToolConfigurationException(f"Failed to load credentials from {CREDS_PATH}: {e}")

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
    """Call Gemini on the prompt and, optionally, the uploaded document."""
    contents: list[types.Part | str] = [prompt]
    if file_content is not None:
        if not mime_type:
            raise APIException("mime_type must be provided when file_content is supplied.", status_code=400)
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

    try:
        response = await CLIENT.aio.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config,
        )
    except Exception as e:
        raise APIException(f"Gemini Vision call failed: {e}", status_code=500)

    if extraction_schema:
        raw = response.text
        if raw is None:
            raise APIException("Vision model returned no text (empty or blocked).", status_code=500)
        try:
            structured_output = json.loads(raw)
        except json.JSONDecodeError as e:
            raise APIException(f"Vision model returned invalid JSON: {e}", status_code=500) from e
        return normalize_structured_vision_output(structured_output)

    text = response.text if response.text is not None else ""
    out = {"text": text}
    if text == "" and getattr(response, "prompt_feedback", None) is not None:
        feedback = response.prompt_feedback
        if getattr(feedback, "block_reason", None) is not None:
            reason = str(feedback.block_reason)
            out["block_reason"] = reason
            logger.warning("Vision response blocked: block_reason=%s", reason)
    return out

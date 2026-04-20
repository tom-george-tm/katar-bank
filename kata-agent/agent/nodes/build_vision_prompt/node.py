from __future__ import annotations

import logging
from agent.schemas.state import VisionState
from agent.nodes.build_vision_prompt.prompt import build_vision_prompt

logger = logging.getLogger(__name__)


async def build_vision_prompt_node(state: VisionState) -> dict:
    """Build a pure vision system prompt (optionally incorporating a custom prompt) and store it in state."""
    logger.info(
        "Building vision-only prompt",
        extra={
            "has_custom_prompt": bool(state.get("custom_prompt")),
            "has_extraction_schema": bool(state.get("extraction_schema")),
        },
    )

    has_extraction_schema = bool(state.get("extraction_schema"))
    pipeline_prompt = build_vision_prompt(
        state.get("custom_prompt"),
        has_extraction_schema=has_extraction_schema,
    )
    return {"pipeline_prompt": pipeline_prompt}

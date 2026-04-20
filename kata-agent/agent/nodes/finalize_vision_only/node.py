from __future__ import annotations

from agent.schemas.state import VisionState


async def finalize_vision_only_node(state: VisionState) -> dict:
    """Assemble the final output payload for pure vision flows (no OCR)."""
    return {
        "final_output": {
            "flow": "vision_pipeline",
            "input": {
                "processor_type": None,
                "mime_type": state.get("mime_type"),
                "custom_prompt": state.get("custom_prompt"),
            },
            "result": {
                "ocr": None,
                "vision": state.get("vision_result"),
            },
        },
    }

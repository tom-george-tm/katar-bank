from __future__ import annotations

from agent.schemas.state import VisionState


async def finalize_ocr_vision_node(state: VisionState) -> dict:
    """Assemble the final output payload for the combined OCR + vision pipeline."""
    pt = state.get("processor_type")
    vision_result = state.get("vision_result")

    return {
        "final_output": {
            "flow": "ocr_vision_pipeline",
            "input": {
                "processor_type": pt.value if pt is not None else None,
                "mime_type": state.get("mime_type"),
                "custom_prompt": state.get("custom_prompt"),
            },
            "result": {
                "ocr": state.get("ocr_result"),
                "vision": vision_result,
            },
        },
    }

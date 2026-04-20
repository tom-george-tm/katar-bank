from __future__ import annotations

from agent.schemas.state import VisionState


async def finalize_ocr_only_node(state: VisionState) -> dict:
    """Assemble the final output payload for OCR-only flows."""
    pt = state.get("processor_type")
    return {
        "final_output": {
            "flow": "ocr_pipeline",
            "input": {
                "processor_type": pt.value if pt is not None else None,
                "mime_type": state.get("mime_type"),
                "custom_prompt": None,
            },
            "result": {
                "ocr": state.get("ocr_result"),
                "vision": None,
            },
        },
    }

from __future__ import annotations

from typing import Optional
import logging

from langgraph.graph import END, StateGraph

from agent.nodes import (
    build_pipeline_prompt_node,
    build_vision_prompt_node,
    docai_ocr_node,
    finalize_ocr_only_node,
    finalize_ocr_vision_node,
    finalize_vision_only_node,
    gemini_vision_node,
    prepare_ocr_input_node,
    route_after_ocr,
    route_after_vision,
    route_from_flow_type,
    router_node,
)
from agent.schemas.state import FlowType, ProcessorType, VisionState


logger = logging.getLogger(__name__)


builder = StateGraph(VisionState)

builder.add_node("router", router_node)
builder.add_node("prepare_ocr_input", prepare_ocr_input_node)
builder.add_node("docai_ocr", docai_ocr_node)
builder.add_node("build_vision_prompt", build_vision_prompt_node)
builder.add_node("build_pipeline_prompt", build_pipeline_prompt_node)
builder.add_node("gemini_vision", gemini_vision_node)
builder.add_node("finalize_ocr_pipeline", finalize_ocr_only_node)
builder.add_node("finalize_vision_pipeline", finalize_vision_only_node)
builder.add_node("finalize_ocr_vision_pipeline", finalize_ocr_vision_node)

builder.set_entry_point("router")

builder.add_conditional_edges(
    "router",
    route_from_flow_type,
    {
        "ocr_pipeline": "prepare_ocr_input",
        "vision_pipeline": "build_vision_prompt",
        "ocr_vision_pipeline": "prepare_ocr_input",
    },
)

builder.add_edge("prepare_ocr_input", "docai_ocr")

builder.add_conditional_edges(
    "docai_ocr",
    route_after_ocr,
    {
        "ocr_pipeline": "finalize_ocr_pipeline",
        "ocr_vision_pipeline": "build_pipeline_prompt",
    },
)

builder.add_edge("build_vision_prompt", "gemini_vision")
builder.add_edge("build_pipeline_prompt", "gemini_vision")

builder.add_conditional_edges(
    "gemini_vision",
    route_after_vision,
    {
        "vision_pipeline": "finalize_vision_pipeline",
        "ocr_vision_pipeline": "finalize_ocr_vision_pipeline",
    },
)

builder.add_edge("finalize_ocr_pipeline", END)
builder.add_edge("finalize_vision_pipeline", END)
builder.add_edge("finalize_ocr_vision_pipeline", END)

vision_graph = builder.compile()


async def run_vision_graph(
    flow_type: FlowType,
    file_content: bytes,
    original_filename: str,
    mime_type: str,
    processor_type: Optional[ProcessorType] = None,
    custom_prompt: Optional[str] = None,
    include_word_confidence: bool = False,
    extraction_schema: Optional[dict] = None,
    include_image_in_vision: bool = True,
) -> dict:
    """Convenience wrapper around the compiled graph."""

    logger.info(
        "Starting vision graph run",
        extra={
            "flow_type": flow_type.value,
            "processor_type": processor_type.value if processor_type else None,
            "mime_type": mime_type,
            "include_image_in_vision": include_image_in_vision,
        },
    )

    initial_state: VisionState = {
        "file_content": file_content,
        "original_filename": original_filename,
        "mime_type": mime_type,
        "flow_type": flow_type,
        "processor_type": processor_type,
        "include_word_confidence": include_word_confidence,
        "custom_prompt": custom_prompt,
        "extraction_schema": extraction_schema,
        "include_image_in_vision": include_image_in_vision,
    }
    final_state = await vision_graph.ainvoke(initial_state)

    logger.info(
        "Finished vision graph run",
        extra={
            "flow_type": flow_type.value,
            "processor_type": processor_type.value if processor_type else None,
        },
    )

    return final_state.get("final_output", final_state)

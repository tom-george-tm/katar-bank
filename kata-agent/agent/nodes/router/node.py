from __future__ import annotations

from agent.schemas.state import VisionState


async def router_node(state: VisionState) -> dict:
    """Entry node: no state updates; pass through to conditional edges."""
    return {}


def route_from_flow_type(state: VisionState) -> str:
    """Decide which branch of the pipeline to run based on the requested flow type."""
    from ..state import FlowType
    flow_type = state.get("flow_type")
    if flow_type not in (FlowType.OCR_PIPELINE, FlowType.VISION_PIPELINE, FlowType.OCR_VISION_PIPELINE):
        raise ValueError(f"Unknown flow type: {flow_type}")
    return flow_type.value

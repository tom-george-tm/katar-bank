from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part, Task, TaskState
from a2a.utils import get_data_parts, new_agent_text_message, new_task

from agent.graph import run_vision_graph
from agent.schemas.state import FlowType, ProcessorType
from agent.services.file_source_service import download_gcs_file

logger = logging.getLogger(__name__)

from agent.schemas.executor import AgentInput


class VisionAgentExecutor(AgentExecutor):
    """A2A Executor for the Vision Agent LangGraph pipeline."""

    def __init__(self, agent_wrapper=None):
        self.agent_wrapper = agent_wrapper

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        start_time = time.perf_counter()
        
        # 1. Extract and validate task
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        
        try:
            # 2. Extract DataPart for configuration
            data_parts = get_data_parts(context.message.parts)
            if not data_parts:
                raise ValueError("Missing DataPart in context message.")
            
            # Map raw dict to AgentInput schema for validation
            raw_input = data_parts[0]
            config = AgentInput(**raw_input)

            # 3. Handle document source (Binary Part vs GCS URI)
            file_content: Optional[bytes] = None
            original_filename: str = "document"

            # Search for the first binary FilePart (mocking get_file_parts logic)
            file_parts = [p for p in context.message.parts if hasattr(p, "filename") and hasattr(p, "content")]
            if file_parts:
                file_content = file_parts[0].content
                original_filename = file_parts[0].filename or "document"
            elif config.gcs_uri:
                file_content, original_filename = await download_gcs_file(config.gcs_uri)
            
            if not file_content:
                raise ValueError("Provide exactly one input source: either an attached FilePart or a gcs_uri.")

            # 4. Flow-specific validation (ported from main.py)
            self._validate_flow(config)

            # 5. MIME type detection
            from agent.services.docai_service import detect_mime_type
            mime_type = detect_mime_type(file_content)

            # 6. Execute Graph
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(f"Processing document with {config.flow_type.value}...", context_id=context.context_id),
            )

            send_image = config.include_image_in_vision if config.flow_type != FlowType.VISION_PIPELINE else True

            result = await run_vision_graph(
                flow_type=config.flow_type,
                file_content=file_content,
                original_filename=original_filename,
                mime_type=mime_type,
                processor_type=config.processor_type,
                custom_prompt=config.custom_prompt,
                include_word_confidence=config.include_word_confidence,
                extraction_schema=config.extraction_schema,
                include_image_in_vision=send_image,
            )

            # 7. Complete Task and return DataPart artifact
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info("Task completed successfully", extra={"request_id": task.id, "elapsed_ms": round(elapsed_ms, 2)})

            await updater.add_artifact(
                [Part(root=DataPart(data=result))],
                name="Vision Processing Result",
            )

            await updater.complete(
                new_agent_text_message(f"Task completed: {task.id}", context_id=context.context_id),
            )

        except Exception as e:
            logger.exception(f"Error executing agent task: {e}")
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(f"Task failed: {str(e)}", context_id=context.context_id),
            )

    def _validate_flow(self, config: AgentInput):
        """Ported validation logic from app/main.py."""
        flow_type = config.flow_type

        # OCR flows (ocr_pipeline, ocr_vision_pipeline)
        if flow_type in {FlowType.OCR_PIPELINE, FlowType.OCR_VISION_PIPELINE}:
            if not config.processor_type:
                raise ValueError("processor_type is required for flows that use OCR.")
            if flow_type == FlowType.OCR_PIPELINE and (config.custom_prompt or config.extraction_schema):
                raise ValueError("custom_prompt/extraction_schema are only supported for vision flows.")

        # vision-pipeline flow
        if flow_type == FlowType.VISION_PIPELINE:
            if config.processor_type is not None:
                raise ValueError("processor_type is only supported for OCR flows.")
            if config.include_word_confidence:
                raise ValueError("include_word_confidence is only supported for OCR flows.")

        # include_image_in_vision relevance
        if flow_type != FlowType.OCR_VISION_PIPELINE and config.include_image_in_vision:
            raise ValueError("include_image_in_vision is only supported for the ocr_vision_pipeline flow.")

    async def cancel(
        self, _request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        task = _request.current_task
        logger.info(f"Cancellation requested for task: {task.id if task else 'unknown'}")
        return None

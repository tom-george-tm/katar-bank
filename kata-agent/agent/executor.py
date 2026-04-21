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
from a2a.types import Message, Part, Task, TaskState

from agent.graph import run_vision_graph
from agent.schemas.state import FlowType, ProcessorType
from agent.services.file_source_service import download_gcs_file

logger = logging.getLogger(__name__)

from agent.schemas.executor import AgentInput


def create_task(message: Message) -> Task:
    """Create a new task from a message."""
    task = Task()
    task.id = str(uuid.uuid4())
    task.state = TaskState.pending
    return task


def create_agent_message(text: str, context_id: str = "") -> Message:
    """Create an agent message with text."""
    message = Message()
    part = Part()
    part.text = text
    message.parts.append(part)
    return message


def extract_data_from_parts(parts) -> Optional[dict]:
    """Extract JSON data from message parts."""
    for part in parts:
        if part.HasField("text") and part.text:
            try:
                return json.loads(part.text)
            except json.JSONDecodeError:
                pass
        elif part.HasField("data") and part.data:
            try:
                return json.loads(part.data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
    return None


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
            task = create_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id if hasattr(task, 'context_id') else "")
        
        try:
            # 2. Extract configuration from message parts
            raw_input = extract_data_from_parts(context.message.parts)
            if not raw_input:
                raise ValueError("Missing configuration data in message parts.")
            
            # Map raw dict to AgentInput schema for validation
            config = AgentInput(**raw_input)

            # 3. Handle document source (Binary Part vs GCS URI)
            file_content: Optional[bytes] = None
            original_filename: str = "document"

            # Search for the first binary FilePart
            for part in context.message.parts:
                if part.HasField("data") and part.data:
                    file_content = part.data
                    if part.HasField("filename"):
                        original_filename = part.filename or "document"
                    break
            
            if not file_content and config.gcs_uri:
                file_content, original_filename = await download_gcs_file(config.gcs_uri)
            
            if not file_content:
                raise ValueError("Provide exactly one input source: either an attached FilePart or a gcs_uri.")

            # 4. Flow-specific validation
            self._validate_flow(config)

            # 5. MIME type detection
            from agent.services.docai_service import detect_mime_type
            mime_type = detect_mime_type(file_content)

            # 6. Execute Graph
            await updater.update_status(
                TaskState.working,
                create_agent_message(f"Processing document with {config.flow_type.value}..."),
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

            # 7. Complete Task and return result
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info("Task completed successfully", extra={"request_id": task.id, "elapsed_ms": round(elapsed_ms, 2)})

            # Create result message with data part
            result_message = Message()
            result_part = Part()
            result_part.data = json.dumps(result).encode("utf-8")
            result_part.media_type = "application/json"
            result_message.parts.append(result_part)

            await updater.add_artifact(
                result_message.parts,
                name="Vision Processing Result",
            )

            await updater.complete(
                create_agent_message(f"Task completed: {task.id}"),
            )

        except Exception as e:
            logger.exception(f"Error executing agent task: {e}")
            await updater.update_status(
                TaskState.failed,
                create_agent_message(f"Task failed: {str(e)}"),
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

import asyncio
import json
import os
from typing import Any, Optional
from uuid import uuid4

import httpx
from google.protobuf.json_format import MessageToDict
from a2a.client import A2ACardResolver, Client, ClientConfig, ClientFactory
from a2a.types import (
    Message,
    GetTaskRequest,
    TaskStatusUpdateEvent,
    Part,
    Role,
    SendMessageRequest,
    SendMessageConfiguration,
)

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_MESSAGE = "Extract all information from this document and summarize it."
UPLOAD_FOLDER = "./upload"

TERMINAL_TASK_STATES = {
    "completed",
    "canceled",
    "failed",
    "rejected",
    "auth_required",
    "unknown",
}


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def dump_json(label: str, payload: Any) -> None:
    print(f"\n{label}:")
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def to_dict(protobuf_msg: Any) -> dict:
    """Convert protobuf message to dict, handling both protobuf and Pydantic models."""
    try:
        # Try protobuf serialization first
        return MessageToDict(protobuf_msg, preserving_proto_field_name=True)
    except (AttributeError, TypeError):
        # Fall back to Pydantic if available
        try:
            return protobuf_msg.model_dump(mode="json", exclude_none=True)
        except (AttributeError, TypeError):
            # Last resort: convert to string
            return {"value": str(protobuf_msg)}


def extract_text(message_payload: dict[str, Any]) -> str:
    parts = message_payload.get("parts", [])
    texts = [
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and part.get("kind") == "text"
    ]
    return "\n".join(text for text in texts if text).strip()


def build_message(
    user_text: str,
    config: dict,
    file_content: Optional[bytes] = None,
    filename: Optional[str] = None
) -> Message:
    parts = [
        Part(text=user_text),
        Part(raw=json.dumps(config).encode()),
    ]
    if file_content:
        parts.append(Part(
            raw=file_content,
            filename=filename,
            media_type="application/octet-stream"
        ))

    return Message(
        role=Role.ROLE_USER,
        parts=parts,
        message_id=uuid4().hex,
    )


async def poll_task_until_terminal(
    client: Client,
    task_id: str,
    poll_interval_seconds: float,
) -> None:
    while True:
        await asyncio.sleep(poll_interval_seconds)
        task = await client.get_task(
            GetTaskRequest(id=task_id),
        )
        task_payload = to_dict(task)
        dump_json("Task update", task_payload)

        state = task_payload.get("status", {}).get("state")
        if state in TERMINAL_TASK_STATES:
            message_payload = task_payload.get("status", {}).get("message")
            if isinstance(message_payload, dict):
                text = extract_text(message_payload)
                if text:
                    print(f"\nFinal task message:\n{text}")
            return


async def call_agent(
    base_url: Optional[str] = None,
    user_message: Optional[str] = None,
    stream: Optional[bool] = None,
    poll_tasks: Optional[bool] = None,
    poll_interval_seconds: float = 2.0,
    file_content: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> dict[str, Any]:
    """Call the agent with the provided parameters.
    
    This is the modular entry point for programmatic use (e.g., testing).
    
    Args:
        base_url: Agent base URL (defaults to A2A_BASE_URL env or DEFAULT_BASE_URL)
        user_message: User message (defaults to A2A_USER_MESSAGE env or DEFAULT_MESSAGE)
        stream: Whether to stream (defaults to A2A_STREAM env or False)
        poll_tasks: Whether to poll tasks (defaults to A2A_POLL_TASK env or True)
        poll_interval_seconds: Poll interval in seconds
        file_content: File binary content (if None, will look in upload folder)
        filename: Filename for the file_content
    
    Returns:
        dict: Result dict with keys: 'success', 'task_id', 'message', 'state'
    """
    # Use provided values or fall back to environment/defaults
    if base_url is None:
        base_url = os.getenv("A2A_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    if user_message is None:
        user_message = os.getenv("A2A_USER_MESSAGE", DEFAULT_MESSAGE)
    if stream is None:
        stream = env_flag("A2A_STREAM")
    if poll_tasks is None:
        poll_tasks = env_flag("A2A_POLL_TASK", default=True)
    
    # If file not provided, try to load from upload folder
    if file_content is None:
        if os.path.exists(UPLOAD_FOLDER):
            files = [f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
            if files:
                filename = files[0]
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                with open(file_path, "rb") as f:
                    file_content = f.read()
                print(f"Found file for upload: {filename} ({len(file_content)} bytes)")
    
    # Default configuration for the Vision Agent
    agent_config = {
        "flow_type": "ocr_vision_pipeline",
        "processor_type": "document_ocr",
        "custom_prompt": user_message,
        "include_word_confidence": True,
        "include_image_in_vision": True
    }
    
    result = {
        "success": False,
        "task_id": None,
        "message": None,
        "state": None,
    }
    
    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        agent_card_payload = to_dict(agent_card)
        dump_json("Resolved agent card", agent_card_payload)

        # The resolver already provides the correct agent card with proper URLs
        # No need to override for local testing
        client = ClientFactory(
            ClientConfig(
                httpx_client=httpx_client,
                streaming=stream,
                polling=False,
            )
        ).create(agent_card)
        try:
            message = build_message(
                user_text=user_message,
                config=agent_config,
                file_content=file_content,
                filename=filename
            )

            if stream:
                print(f"\nSending streaming request to {base_url}")
            else:
                print(f"\nSending request to {base_url}")

            # Wrap the message in a SendMessageRequest
            config = SendMessageConfiguration(return_immediately=False)
            send_request = SendMessageRequest(
                message=message,
                configuration=config
            )

            async for event in client.send_message(send_request):
                if isinstance(event, Message):
                    response_payload = to_dict(event)
                    dump_json("Message response", response_payload)
                    text = extract_text(response_payload)
                    if text:
                        print(f"\nAgent reply:\n{text}")
                        result["message"] = text
                        result["success"] = True
                        result["state"] = "completed"
                    return result

                task, update = event
                task_payload = to_dict(task)
                label = "Streaming task event" if stream else "Task response"
                dump_json(label, task_payload)

                if isinstance(update, TaskStatusUpdateEvent):
                    update_payload = to_dict(update)
                    dump_json("Task status update", update_payload)

                state = task_payload.get("status", {}).get("state")
                task_id = task_payload.get("id")
                print(f"\nTask returned: id={task_id} state={state}")
                
                result["task_id"] = task_id
                result["state"] = state

                if state in TERMINAL_TASK_STATES:
                    message_payload = task_payload.get("status", {}).get("message")
                    if isinstance(message_payload, dict):
                        text = extract_text(message_payload)
                        if text:
                            print(f"\nFinal task message:\n{text}")
                            result["message"] = text
                    result["success"] = state == "completed"
                    return result

                if not stream and poll_tasks and task_id:
                    await poll_task_until_terminal(
                        client=client,
                        task_id=task_id,
                        poll_interval_seconds=poll_interval_seconds,
                    )
                    result["success"] = True
                    return result
        finally:
            await client.close()
    
    return result


async def run() -> None:
    """Main entry point for direct execution.
    
    Calls the modular call_agent function for backward compatibility.
    """
    await call_agent()


if __name__ == "__main__":
    asyncio.run(run())

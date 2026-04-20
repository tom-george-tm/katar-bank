import asyncio
import json
import os
from typing import Any, Optional
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, Client, ClientConfig, ClientFactory
from a2a.types import (
    Message,
    TaskQueryParams,
    TaskStatusUpdateEvent,
    TextPart,
    DataPart,
    FilePart,
    Part,
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
        Part(root=TextPart(text=user_text)),
        Part(root=DataPart(data=config)),
    ]
    if file_content:
        parts.append(Part(root=FilePart(content=file_content, filename=filename)))

    return Message(
        role="user",
        parts=parts,
        messageId=uuid4().hex,
    )


async def poll_task_until_terminal(
    client: Client,
    task_id: str,
    poll_interval_seconds: float,
) -> None:
    while True:
        await asyncio.sleep(poll_interval_seconds)
        task = await client.get_task(
            TaskQueryParams(id=task_id),
        )
        task_payload = task.model_dump(mode="json", exclude_none=True)
        dump_json("Task update", task_payload)

        state = task_payload.get("status", {}).get("state")
        if state in TERMINAL_TASK_STATES:
            message_payload = task_payload.get("status", {}).get("message")
            if isinstance(message_payload, dict):
                text = extract_text(message_payload)
                if text:
                    print(f"\nFinal task message:\n{text}")
            return


async def run() -> None:
    base_url = os.getenv("A2A_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    user_message = os.getenv("A2A_USER_MESSAGE", DEFAULT_MESSAGE)
    stream = env_flag("A2A_STREAM")
    poll_tasks = env_flag("A2A_POLL_TASK", default=True)
    poll_interval_seconds = float(os.getenv("A2A_POLL_INTERVAL_SECONDS", "2"))

    # --- Prepare document and configuration ---
    # Pick the first file from the upload folder if it exists
    file_content: Optional[bytes] = None
    filename: Optional[str] = None
    
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

    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        agent_card_payload = agent_card.model_dump(mode="json", exclude_none=True)
        dump_json("Resolved agent card", agent_card_payload)

        # Override the transport URL for local testing
        agent_card = agent_card.model_copy(
            update={"url": base_url, "preferred_transport": "JSONRPC"}
        )
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

            async for event in client.send_message(message):
                if isinstance(event, Message):
                    response_payload = event.model_dump(mode="json", exclude_none=True)
                    dump_json("Message response", response_payload)
                    text = extract_text(response_payload)
                    if text:
                        print(f"\nAgent reply:\n{text}")
                    return

                task, update = event
                task_payload = task.model_dump(mode="json", exclude_none=True)
                label = "Streaming task event" if stream else "Task response"
                dump_json(label, task_payload)

                if isinstance(update, TaskStatusUpdateEvent):
                    update_payload = update.model_dump(mode="json", exclude_none=True)
                    dump_json("Task status update", update_payload)

                state = task_payload.get("status", {}).get("state")
                task_id = task_payload.get("id")
                print(f"\nTask returned: id={task_id} state={state}")

                if state in TERMINAL_TASK_STATES:
                    message_payload = task_payload.get("status", {}).get("message")
                    if isinstance(message_payload, dict):
                        text = extract_text(message_payload)
                        if text:
                            print(f"\nFinal task message:\n{text}")
                    return

                if not stream and poll_tasks and task_id:
                    await poll_task_until_terminal(
                        client=client,
                        task_id=task_id,
                        poll_interval_seconds=poll_interval_seconds,
                    )
                    return
        finally:
            await client.close()


if __name__ == "__main__":
    asyncio.run(run())

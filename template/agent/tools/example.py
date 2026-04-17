"""Example custom tool for the ADK template.

This is a simple, pure-Python helper that you can wrap as an ADK tool
if desired. It demonstrates how to organize reusable tool logic under
`agent/tools/`.
"""

from __future__ import annotations

from typing import Any, Dict, List


def summarize_last_user_message(messages: List[Dict[str, Any]]) -> str:
    """Return a short summary of the last user message in the list."""
    last_user_content = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_content = str(msg.get("content", ""))
            break

    if not last_user_content:
        return "(tool) No user message found."

    length = len(last_user_content)
    preview = last_user_content[:50] + ("…" if len(last_user_content) > 50 else "")
    return f"(tool) Last user message has {length} characters. Preview: {preview!r}"


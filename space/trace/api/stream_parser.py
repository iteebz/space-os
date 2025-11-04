"""Stream-JSON parser: extract execution events from Claude Code stream output."""

import json
from collections.abc import Iterator


def parse_stream_json(stdout_stream) -> Iterator[dict]:
    """Parse stream-json events from Claude Code output.

    Yields structured events from stream-json format (one JSON object per line).

    Args:
        stdout_stream: File-like object or iterator of lines from Claude Code

    Yields:
        Dicts with event type and relevant data
    """
    for line in stdout_stream:
        if not line.strip():
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type")

        if event_type == "system":
            yield {
                "event": "system_init",
                "session_id": event.get("session_id"),
                "cwd": event.get("cwd"),
                "tools": event.get("tools", []),
            }

        elif event_type == "assistant":
            msg = event.get("message", {})
            content = msg.get("content", [])

            for item in content:
                if item.get("type") == "tool_use":
                    yield {
                        "event": "tool_call",
                        "tool": item.get("name"),
                        "tool_id": item.get("id"),
                        "input": item.get("input"),
                    }
                elif item.get("type") == "text":
                    yield {
                        "event": "text",
                        "text": item.get("text"),
                    }

        elif event_type == "user":
            msg = event.get("message", {})
            content = msg.get("content", [])

            for item in content:
                if item.get("type") == "tool_result":
                    yield {
                        "event": "tool_result",
                        "tool_id": item.get("tool_use_id"),
                        "result": item.get("content"),
                    }

        elif event_type == "result":
            yield {
                "event": "completion",
                "status": event.get("subtype"),
                "session_id": event.get("session_id"),
                "result": event.get("result"),
                "duration_ms": event.get("duration_ms"),
            }

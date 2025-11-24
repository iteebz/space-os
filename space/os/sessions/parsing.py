"""Session parsing: extract messages from provider JSONL files."""

import json


def parse_jsonl_message(line: str) -> dict | None:
    """Parse single JSONL line from provider session file.

    Args:
        line: JSON string from session file

    Returns:
        Dict with 'role' and 'text' keys, or None if invalid/empty
    """
    if not line.strip():
        return None

    try:
        obj = json.loads(line)
        msg_type = obj.get("type")
        message = obj.get("message", {})

        if msg_type == "assistant":
            content = message.get("content", [])
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    return {"role": "assistant", "text": item.get("text", "")}
        elif msg_type == "user":
            content = message.get("content", [])
            if isinstance(content, str):
                return {"role": "user", "text": content}
    except json.JSONDecodeError:
        pass

    return None

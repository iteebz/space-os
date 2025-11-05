"""Claude session JSONL parser tests."""

import json
import tempfile
from pathlib import Path

from space.lib.providers.claude import Claude


def test_parse_tool_call():
    """Parse Claude tool_use event."""
    jsonl_content = json.dumps(
        {
            "type": "assistant",
            "timestamp": "2025-11-04T10:00:00Z",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_123",
                        "name": "Bash",
                        "input": {"command": "ls -la"},
                    }
                ],
            },
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        messages = Claude.parse(temp_path)

        assert len(messages) == 2
        assert messages[0].type == "tool_call"
        assert messages[0].content["tool_name"] == "Bash"
        assert messages[0].content["input"] == {"command": "ls -la"}
        assert messages[1].type == "message"
        assert messages[1].content["role"] == "assistant"
    finally:
        temp_path.unlink()


def test_parse_tool_result():
    """Parse Claude tool_result event."""
    jsonl_content = json.dumps(
        {
            "type": "user",
            "timestamp": "2025-11-04T10:00:05Z",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_123",
                        "content": "output from command",
                        "is_error": False,
                    }
                ],
            },
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        messages = Claude.parse(temp_path)

        assert len(messages) == 2
        assert messages[0].type == "tool_result"
        assert messages[0].content["output"] == "output from command"
        assert messages[0].content["is_error"] is False
        assert messages[1].type == "message"
        assert messages[1].content["role"] == "user"
    finally:
        temp_path.unlink()


def test_parse_text_response():
    """Parse Claude text response."""
    jsonl_content = json.dumps(
        {
            "type": "assistant",
            "timestamp": "2025-11-04T10:00:10Z",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Here are the files in the directory",
                    }
                ],
            },
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        messages = Claude.parse(temp_path)

        assert len(messages) == 2
        assert messages[0].type == "text"
        assert messages[0].content == "Here are the files in the directory"
        assert messages[1].type == "message"
        assert messages[1].content["role"] == "assistant"
    finally:
        temp_path.unlink()


def test_parse_multiple_events():
    """Parse session with multiple events in order."""
    lines = [
        json.dumps(
            {
                "type": "assistant",
                "timestamp": "2025-11-04T10:00:00Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_123",
                            "name": "Bash",
                            "input": {"command": "pwd"},
                        }
                    ],
                },
            }
        ),
        json.dumps(
            {
                "type": "user",
                "timestamp": "2025-11-04T10:00:05Z",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_123",
                            "content": "/home/user",
                            "is_error": False,
                        }
                    ],
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "timestamp": "2025-11-04T10:00:10Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "Current directory is /home/user",
                        }
                    ],
                },
            }
        ),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("\n".join(lines))
        f.flush()
        temp_path = Path(f.name)

    try:
        messages = Claude.parse(temp_path)

        assert len(messages) == 6
        assert messages[0].type == "tool_call"
        assert messages[1].type == "message"
        assert messages[2].type == "tool_result"
        assert messages[3].type == "message"
        assert messages[4].type == "text"
        assert messages[5].type == "message"
    finally:
        temp_path.unlink()


def test_parse_missing_file():
    """Handle missing file gracefully."""
    events = Claude.parse("/nonexistent/path.jsonl")
    assert events == []


def test_parse_empty_file():
    """Handle empty file gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        temp_path = Path(f.name)

    try:
        messages = Claude.parse(temp_path)
        assert messages == []
    finally:
        temp_path.unlink()

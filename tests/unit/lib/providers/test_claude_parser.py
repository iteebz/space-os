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
        events = Claude.parse_jsonl(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].data.tool_id == "toolu_123"
        assert events[0].data.tool_name == "Bash"
        assert events[0].data.input == {"command": "ls -la"}
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
        events = Claude.parse_jsonl(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_result"
        assert events[0].data.tool_id == "toolu_123"
        assert events[0].data.output == "output from command"
        assert events[0].data.is_error is False
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
        events = Claude.parse_jsonl(temp_path)

        assert len(events) == 1
        assert events[0].type == "text"
        assert events[0].data.content == "Here are the files in the directory"
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
        events = Claude.parse_jsonl(temp_path)

        assert len(events) == 3
        assert events[0].type == "tool_call"
        assert events[1].type == "tool_result"
        assert events[2].type == "text"
    finally:
        temp_path.unlink()


def test_parse_missing_file():
    """Handle missing file gracefully."""
    events = Claude.parse_jsonl("/nonexistent/path.jsonl")
    assert events == []


def test_parse_empty_file():
    """Handle empty file gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        temp_path = Path(f.name)

    try:
        events = Claude.parse_jsonl(temp_path)
        assert events == []
    finally:
        temp_path.unlink()

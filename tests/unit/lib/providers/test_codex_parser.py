"""Codex (OpenAI) parser tests - reference implementation for tool_calls handling."""

import json
import tempfile
from pathlib import Path

from space.lib.providers.codex import Codex


def test_parse_tool_call():
    """Boundary: Parse Codex tool_call event."""
    jsonl_content = json.dumps(
        {
            "role": "assistant",
            "timestamp": "2025-11-04T10:00:00Z",
            "content": "Let me run that command",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "arguments": '{"command": "ls -la"}',
                    },
                }
            ],
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Codex.parse_jsonl(temp_path)

        assert len(events) == 2
        assert events[0].type == "text"
        assert events[1].type == "tool_call"
        assert events[1].data.tool_id == "call_123"
        assert events[1].data.tool_name == "bash"
        assert events[1].data.input == {"command": "ls -la"}
    finally:
        temp_path.unlink()


def test_parse_tool_result():
    """Boundary: Parse Codex tool role message."""
    jsonl_content = json.dumps(
        {
            "role": "tool",
            "timestamp": "2025-11-04T10:00:05Z",
            "tool_call_id": "call_123",
            "content": "file1.txt\nfile2.txt",
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Codex.parse_jsonl(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_result"
        assert events[0].data.tool_id == "call_123"
        assert events[0].data.output == "file1.txt\nfile2.txt"
    finally:
        temp_path.unlink()


def test_parse_malformed_json_arguments():
    """Boundary: Handle malformed JSON in tool arguments."""
    jsonl_content = json.dumps(
        {
            "role": "assistant",
            "timestamp": "2025-11-04T10:00:00Z",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "arguments": "not valid json",
                    },
                }
            ],
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Codex.parse_jsonl(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].data.input == {"raw": "not valid json"}
    finally:
        temp_path.unlink()


def test_parse_multiple_tool_calls():
    """Contract: Single message with multiple tool calls."""
    jsonl_content = json.dumps(
        {
            "role": "assistant",
            "timestamp": "2025-11-04T10:00:00Z",
            "content": "Running checks",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "arguments": '{"command": "pwd"}',
                    },
                },
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "arguments": '{"command": "ls"}',
                    },
                },
            ],
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Codex.parse_jsonl(temp_path)

        assert len(events) == 3
        assert events[0].type == "text"
        assert events[1].type == "tool_call"
        assert events[1].data.tool_id == "call_1"
        assert events[2].type == "tool_call"
        assert events[2].data.tool_id == "call_2"
    finally:
        temp_path.unlink()


def test_parse_empty_file():
    """Boundary: Handle empty JSONL gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        temp_path = Path(f.name)

    try:
        events = Codex.parse_jsonl(temp_path)
        assert events == []
    finally:
        temp_path.unlink()


def test_parse_missing_file():
    """Boundary: Handle missing file gracefully."""
    events = Codex.parse_jsonl("/nonexistent/path.jsonl")
    assert events == []

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
        events = Codex.parse(temp_path)

        assert len(events) == 2
        assert events[0].type == "text"
        assert events[1].type == "tool_call"
        assert events[1].content["tool_name"] == "bash"
        assert events[1].content["input"] == {"command": "ls -la"}
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
        events = Codex.parse(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_result"
        assert events[0].content["output"] == "file1.txt\nfile2.txt"
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
        events = Codex.parse(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].content["input"] == {"raw": "not valid json"}
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
        events = Codex.parse(temp_path)

        assert len(events) == 3
        assert events[0].type == "text"
        assert events[1].type == "tool_call"
        assert events[2].type == "tool_call"
    finally:
        temp_path.unlink()


def test_parse_empty_file():
    """Boundary: Handle empty JSONL gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        temp_path = Path(f.name)

    try:
        events = Codex.parse(temp_path)
        assert events == []
    finally:
        temp_path.unlink()


def test_parse_missing_file():
    """Boundary: Handle missing file gracefully."""
    events = Codex.parse("/nonexistent/path.jsonl")
    assert events == []


def test_tool_name_normalization_shell():
    """Contract: Codex 'shell' normalizes to 'Bash'."""
    jsonl_content = json.dumps(
        {
            "timestamp": "2025-11-04T10:00:00Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "shell",
                "arguments": '{"command": ["bash", "-lc", "ls -la"], "workdir": "/tmp"}',
                "call_id": "call_abc",
            },
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Codex.parse(temp_path)
        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].content["tool_name"] == "Bash"
        assert events[0].content["input"]["command"] == "ls -la"
    finally:
        temp_path.unlink()


def test_tool_name_normalization_str_replace_editor():
    """Contract: Codex 'str_replace_editor' normalizes to 'Edit'."""
    jsonl_content = json.dumps(
        {
            "timestamp": "2025-11-04T10:00:00Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "str_replace_editor",
                "arguments": '{"path": "/tmp/test.py", "old_str": "foo", "new_str": "bar"}',
                "call_id": "call_def",
            },
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Codex.parse(temp_path)
        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].content["tool_name"] == "Edit"
        assert events[0].content["input"]["path"] == "/tmp/test.py"
    finally:
        temp_path.unlink()


def test_function_call_output_parsing():
    """Contract: Parse function_call_output with nested JSON output."""
    jsonl_content = json.dumps(
        {
            "timestamp": "2025-11-04T10:00:05Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call_abc",
                "output": '{"output": "file1.txt\\nfile2.txt", "metadata": {"exit_code": 0}}',
            },
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Codex.parse(temp_path)
        assert len(events) == 1
        assert events[0].type == "tool_result"
        assert events[0].content["output"] == "file1.txt\nfile2.txt"
        assert events[0].content["is_error"] is False
    finally:
        temp_path.unlink()


def test_function_call_output_error():
    """Contract: Detect errors from non-zero exit code."""
    jsonl_content = json.dumps(
        {
            "timestamp": "2025-11-04T10:00:05Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call_abc",
                "output": '{"output": "command not found", "metadata": {"exit_code": 127}}',
            },
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Codex.parse(temp_path)
        assert len(events) == 1
        assert events[0].type == "tool_result"
        assert events[0].content["is_error"] is True
    finally:
        temp_path.unlink()

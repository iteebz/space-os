"""Gemini parser tests - reference implementation for function call handling."""

import json
import tempfile
from pathlib import Path

from space.lib.providers.gemini import Gemini


def test_parse_function_call():
    """Boundary: Parse Gemini functionCall event."""
    jsonl_content = json.dumps(
        {
            "type": "model",
            "timestamp": "2025-11-04T10:00:00Z",
            "parts": [
                {
                    "functionCall": {
                        "name": "bash",
                        "args": {"command": "ls -la"},
                    }
                }
            ],
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Gemini.parse_jsonl(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].data.tool_id == "bash"
        assert events[0].data.tool_name == "bash"
        assert events[0].data.input == {"command": "ls -la"}
    finally:
        temp_path.unlink()


def test_parse_function_result():
    """Boundary: Parse Gemini functionResult event."""
    jsonl_content = json.dumps(
        {
            "type": "user",
            "timestamp": "2025-11-04T10:00:05Z",
            "parts": [
                {
                    "functionResult": {
                        "name": "bash",
                        "response": {"result": "file1.txt\nfile2.txt"},
                    }
                }
            ],
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Gemini.parse_jsonl(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_result"
        assert events[0].data.tool_id == "bash"
        assert events[0].data.output == "file1.txt\nfile2.txt"
    finally:
        temp_path.unlink()


def test_parse_text_response():
    """Boundary: Parse Gemini text response."""
    jsonl_content = json.dumps(
        {
            "type": "model",
            "timestamp": "2025-11-04T10:00:10Z",
            "parts": [{"text": "Here are the files"}],
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Gemini.parse_jsonl(temp_path)

        assert len(events) == 1
        assert events[0].type == "text"
        assert events[0].data.content == "Here are the files"
    finally:
        temp_path.unlink()


def test_parse_mixed_parts():
    """Contract: Model message with both text and functionCall."""
    jsonl_content = json.dumps(
        {
            "type": "model",
            "timestamp": "2025-11-04T10:00:00Z",
            "parts": [
                {"text": "Let me check that"},
                {
                    "functionCall": {
                        "name": "bash",
                        "args": {"command": "pwd"},
                    }
                },
            ],
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(jsonl_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        events = Gemini.parse_jsonl(temp_path)

        assert len(events) == 2
        assert events[0].type == "text"
        assert events[1].type == "tool_call"
    finally:
        temp_path.unlink()


def test_parse_empty_file():
    """Boundary: Handle empty JSONL gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        temp_path = Path(f.name)

    try:
        events = Gemini.parse_jsonl(temp_path)
        assert events == []
    finally:
        temp_path.unlink()


def test_parse_missing_file():
    """Boundary: Handle missing file gracefully."""
    events = Gemini.parse_jsonl("/nonexistent/path.jsonl")
    assert events == []

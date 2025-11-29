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
        events = Gemini.parse(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].content["tool_name"] == "bash"
        assert events[0].content["input"] == {"command": "ls -la"}
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
        events = Gemini.parse(temp_path)

        assert len(events) == 1
        assert events[0].type == "tool_result"
        assert events[0].content["output"] == "file1.txt\nfile2.txt"
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
        events = Gemini.parse(temp_path)

        assert len(events) == 1
        assert events[0].type == "text"
        assert events[0].content == "Here are the files"
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
        events = Gemini.parse(temp_path)

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
        events = Gemini.parse(temp_path)
        assert events == []
    finally:
        temp_path.unlink()


def test_parse_missing_file():
    """Boundary: Handle missing file gracefully."""
    events = Gemini.parse("/nonexistent/path.jsonl")
    assert events == []


def test_to_jsonl():
    """Convert Gemini JSON to JSONL format."""
    gemini_json = {
        "sessionId": "test-123",
        "messages": [
            {"type": "user", "content": "Hello", "timestamp": "2025-01-01T00:00:00Z"},
            {"type": "model", "content": "Hi there", "timestamp": "2025-01-01T00:00:01Z"},
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(gemini_json, f)
        temp_path = Path(f.name)

    try:
        result = Gemini.to_jsonl(temp_path)
        lines = result.strip().split("\n")

        assert len(lines) == 2
        msg1 = json.loads(lines[0])
        msg2 = json.loads(lines[1])

        assert msg1["role"] == "user"
        assert msg1["content"] == "Hello"
        assert msg2["role"] == "assistant"
        assert msg2["content"] == "Hi there"
    finally:
        temp_path.unlink()


def test_to_jsonl_empty():
    """Handle empty Gemini JSON gracefully."""
    empty_json = {"sessionId": "test-456", "messages": []}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(empty_json, f)
        temp_path = Path(f.name)

    try:
        result = Gemini.to_jsonl(temp_path)
        assert result == ""
    finally:
        temp_path.unlink()


def test_to_jsonl_malformed():
    """Gracefully handle malformed Gemini JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json")
        temp_path = Path(f.name)

    try:
        result = Gemini.to_jsonl(temp_path)
        assert result == ""
    finally:
        temp_path.unlink()


def test_ingest():
    """Ingest one Gemini session: convert JSON to JSONL."""
    gemini_json = {
        "sessionId": "test-ingest",
        "messages": [
            {"type": "user", "content": "Hello", "timestamp": "2025-01-01T00:00:00Z"},
            {"type": "model", "content": "Hi there", "timestamp": "2025-01-01T00:00:01Z"},
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        src_file = Path(tmpdir) / "source.json"
        json.dump(gemini_json, src_file.open("w"))

        dest_dir = Path(tmpdir) / "dest"
        session = {
            "session_id": "test-ingest",
            "file_path": str(src_file),
        }

        success = Gemini.ingest(session, dest_dir)

        assert success
        assert (dest_dir / "test-ingest.jsonl").exists()
        content = (dest_dir / "test-ingest.jsonl").read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 2


def test_tool_name_normalization_shell():
    """Contract: Gemini 'Shell' normalizes to 'Bash'."""
    jsonl_content = json.dumps(
        {
            "type": "model",
            "timestamp": "2025-11-04T10:00:00Z",
            "parts": [
                {
                    "functionCall": {
                        "name": "Shell",
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
        events = Gemini.parse(temp_path)
        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].content["tool_name"] == "Bash"
    finally:
        temp_path.unlink()


def test_tool_name_normalization_write_file():
    """Contract: Gemini 'WriteFile' normalizes to 'Write'."""
    jsonl_content = json.dumps(
        {
            "type": "model",
            "timestamp": "2025-11-04T10:00:00Z",
            "parts": [
                {
                    "functionCall": {
                        "name": "WriteFile",
                        "args": {"path": "/tmp/test.txt", "content": "hello"},
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
        events = Gemini.parse(temp_path)
        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].content["tool_name"] == "Write"
    finally:
        temp_path.unlink()


def test_tool_name_normalization_read_file():
    """Contract: Gemini 'ReadFile' normalizes to 'Read'."""
    jsonl_content = json.dumps(
        {
            "type": "model",
            "timestamp": "2025-11-04T10:00:00Z",
            "parts": [
                {
                    "functionCall": {
                        "name": "ReadFile",
                        "args": {"path": "/tmp/test.txt"},
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
        events = Gemini.parse(temp_path)
        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].content["tool_name"] == "Read"
    finally:
        temp_path.unlink()


def test_tool_name_normalization_search_text():
    """Contract: Gemini 'SearchText' normalizes to 'Grep'."""
    jsonl_content = json.dumps(
        {
            "type": "model",
            "timestamp": "2025-11-04T10:00:00Z",
            "parts": [
                {
                    "functionCall": {
                        "name": "SearchText",
                        "args": {"pattern": "TODO", "path": "/tmp"},
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
        events = Gemini.parse(temp_path)
        assert len(events) == 1
        assert events[0].type == "tool_call"
        assert events[0].content["tool_name"] == "Grep"
    finally:
        temp_path.unlink()

"""Tests for session sync: file copy/conversion with state tracking."""

import json
import tempfile
from pathlib import Path

from space.os.sessions.api.sync import _to_jsonl


def test_gemini_json_to_jsonl():
    """Convert Gemini JSON to JSONL format."""
    gemini_json = {
        "sessionId": "test-123",
        "messages": [
            {"role": "user", "content": "Hello", "timestamp": "2025-01-01T00:00:00Z"},
            {"role": "model", "content": "Hi there", "timestamp": "2025-01-01T00:00:01Z"},
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(gemini_json, f)
        temp_path = Path(f.name)

    try:
        result = _to_jsonl(temp_path)
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


def test_gemini_json_to_jsonl_empty():
    """Handle empty Gemini JSON gracefully."""
    empty_json = {"sessionId": "test-456", "messages": []}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(empty_json, f)
        temp_path = Path(f.name)

    try:
        result = _to_jsonl(temp_path)
        assert result == ""
    finally:
        temp_path.unlink()


def test_gemini_json_to_jsonl_malformed():
    """Gracefully handle malformed Gemini JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json")
        temp_path = Path(f.name)

    try:
        result = _to_jsonl(temp_path)
        assert result == ""
    finally:
        temp_path.unlink()


def test_sync_state_persistence():
    """Load and save sync state tracking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "sync_state.json"

        state = {
            "claude_abc123": 1700000000.0,
            "gemini_def456": 1700000100.0,
        }

        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2))

        loaded = json.loads(state_file.read_text())
        assert loaded["claude_abc123"] == 1700000000.0
        assert loaded["gemini_def456"] == 1700000100.0

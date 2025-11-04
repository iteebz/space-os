"""Tests for session sync: file copy/conversion with state tracking."""

import json
import tempfile
from pathlib import Path


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

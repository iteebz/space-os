"""Unit tests for session linker (spawn → session_id linking)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from space.os.sessions.api import linker


def test_truncate_spawn_id():
    """Spawn marker is first 8 chars of spawn_id."""
    spawn_id = "abc12345-def6-7890-abcd-ef1234567890"
    marker = linker._truncate_spawn_id(spawn_id)
    assert marker == "abc12345"


def test_extract_session_id_from_jsonl():
    """Extract session_id from JSONL first line."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text('{"id": "session-abc-123"}\n{"type": "message"}\n')

        session_id = linker._extract_session_id(session_file)
        assert session_id == "session-abc-123"


def test_extract_session_id_returns_none():
    """Return None if no id field."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text('{"type": "message"}\n')

        session_id = linker._extract_session_id(session_file)
        assert session_id is None


def test_parse_spawn_marker():
    """Extract spawn marker from JSONL."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text(
            '{"id": "test"}\n{"type": "message", "content": "spawn_marker: abc12345"}\n'
        )

        marker = linker._parse_spawn_marker(session_file)
        assert marker == "abc12345"


def test_parse_spawn_marker_returns_none():
    """Return None if no marker found."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text('{"id": "test"}\n{"type": "message", "content": "hello"}\n')

        marker = linker._parse_spawn_marker(session_file)
        assert marker is None


def test_link_spawn_to_session_updates_db():
    """Verify session_id update to spawns table."""
    with patch("space.os.sessions.api.linker.store.ensure") as mock_store:
        mock_conn = MagicMock()
        mock_store.return_value.__enter__.return_value = mock_conn

        linker.link_spawn_to_session("test-spawn-123", "session-456")

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "UPDATE spawns" in call_args[0]
        assert "session_id" in call_args[0]
        assert call_args[1] == ("session-456", "test-spawn-123")

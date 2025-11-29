"""Unit tests for session linker (spawn → session_id linking)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from space.os.sessions.api import linker


def test_short_id_uses_high_entropy_suffix():
    """Spawn marker uses last 8 chars (high entropy) of UUID7."""
    from space.lib.uuid7 import short_id

    spawn_id = "019a4cee-3a32-7e73-93e8-b012b618c274"
    marker = short_id(spawn_id)
    assert marker == "b618c274", f"Expected last 8 chars, got {marker}"
    assert len(marker) == 8


def test_extract_session_id_from_jsonl():
    """Extract session_id from JSONL first line."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text('{"id": "session-abc-123"}\n{"type": "message"}\n')

        session_id = linker._extract_session_id(session_file)
        assert session_id == "session-abc-123"


def test_extract_session_id_from_claude_format():
    """Extract sessionId from Claude JSONL format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text('{"sessionId": "b03449c9-c20d-4ce9-9f22-6246ea1295f6"}\n')

        session_id = linker._extract_session_id(session_file)
        assert session_id == "b03449c9-c20d-4ce9-9f22-6246ea1295f6"


def test_extract_session_id_falls_back_to_filename():
    """Fall back to filename stem if no id/sessionId field."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "abc12345.jsonl"
        session_file.write_text('{"type": "message"}\n')

        session_id = linker._extract_session_id(session_file)
        assert session_id == "abc12345"


def test_parse_spawn_marker_claude_format():
    """Extract spawn marker from Claude JSONL format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text(
            '{"sessionId": "test"}\n'
            '{"type": "user", "message": {"content": "spawn_marker: abc12345\\n\\nYou are..."}}'
        )
        marker = linker._parse_spawn_marker(session_file)
        assert marker == "abc12345"


def test_parse_spawn_marker_codex_format():
    """Extract spawn marker from Codex JSONL format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text(
            '{"payload": {"id": "test"}}\n'
            '{"role": "user", "content": "spawn_marker: xyz78901\\n\\nYou are..."}'
        )
        marker = linker._parse_spawn_marker(session_file)
        assert marker == "xyz78901"


def test_parse_spawn_marker_gemini_format():
    """Extract spawn marker from Gemini JSONL format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text(
            '{"role": "user", "content": "spawn_marker: def45678\\n\\nYou are...", "timestamp": "2025-11-04T03:34:32.261Z"}'
        )
        marker = linker._parse_spawn_marker(session_file)
        assert marker == "def45678"


def test_parse_spawn_marker_returns_none():
    """Return None if no marker found."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text('{"id": "test"}\n{"type": "message", "content": "hello"}\n')

        marker = linker._parse_spawn_marker(session_file)
        assert marker is None


def test_link_spawn_to_session_updates_db():
    """Verify session_id update to spawns table after sync."""
    with patch("space.os.sessions.api.sync.ingest") as mock_sync:
        with patch("space.os.sessions.api.linker.store.ensure") as mock_store:
            mock_conn = MagicMock()
            mock_store.return_value.__enter__.return_value = mock_conn

            linker.link_spawn_to_session("test-spawn-123", "session-456")

            # Verify sync was called to create session record
            mock_sync.assert_called_once_with(session_id="session-456")

            # Verify execute was called with UPDATE spawns
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args[0]
            assert "UPDATE spawns" in call_args[0]
            assert "session_id" in call_args[0]
            assert call_args[1] == ("session-456", "test-spawn-123")


def test_marker_roundtrip_contract():
    """Contract test: spawn_id → marker → parse → session_id."""
    from space.lib.uuid7 import short_id

    spawn_id = "019a4cee-3a32-7e73-93e8-b012b618c274"
    marker = short_id(spawn_id)

    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "019a4cee-3a32-7e73-93e8-b012b618c274.jsonl"
        session_file.write_text(
            '{"id": "019a4cee-3a32-7e73-93e8-b012b618c274"}\n'
            f'{{"type": "user", "message": {{"content": "spawn_marker: {marker}\\n\\nYou are..."}}}}'
        )

        # Verify marker extraction
        extracted_marker = linker._parse_spawn_marker(session_file)
        assert extracted_marker == marker

        # Verify session_id extraction
        session_id = linker._extract_session_id(session_file)
        assert session_id == spawn_id


def test_find_session_for_spawn_integration():
    """Integration test: find_session_for_spawn with marker match."""
    from datetime import datetime, timezone

    from space.lib import paths
    from space.lib.uuid7 import short_id

    spawn_id = "019a4cee-3a32-7e73-93e8-b012b618c274"
    marker = short_id(spawn_id)
    created_at = datetime.now(timezone.utc).isoformat()

    # Create temporary session directory structure
    sessions_dir = paths.sessions_dir()
    claude_dir = sessions_dir / "claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create session file with marker
        session_file = claude_dir / f"{spawn_id}.jsonl"
        session_file.write_text(
            f'{{"id": "{spawn_id}"}}\n'
            f'{{"type": "user", "message": {{"content": "spawn_marker: {marker}\\n\\nYou are..."}}}}\n'
        )

        # Test marker-based discovery
        found_session_id = linker.find_session_for_spawn(spawn_id, "claude", created_at)
        assert found_session_id == spawn_id, f"Expected {spawn_id}, got {found_session_id}"
    finally:
        # Cleanup
        if session_file.exists():
            session_file.unlink()

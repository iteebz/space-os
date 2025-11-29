"""Unit tests for session linker (spawn → session_id linking)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from space.lib.providers import Claude, Codex, Gemini
from space.lib.providers.base import parse_spawn_marker
from space.os.sessions import linker


def test_short_id_uses_high_entropy_suffix():
    """Spawn marker uses last 8 chars (high entropy) of UUID7."""
    from space.lib.uuid7 import short_id

    spawn_id = "019a4cee-3a32-7e73-93e8-b012b618c274"
    marker = short_id(spawn_id)
    assert marker == "b618c274", f"Expected last 8 chars, got {marker}"
    assert len(marker) == 8


def test_session_id_from_contents_claude():
    """Extract sessionId from Claude JSONL format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text('{"sessionId": "b03449c9-c20d-4ce9-9f22-6246ea1295f6"}\n')
        assert (
            Claude.session_id_from_contents(session_file) == "b03449c9-c20d-4ce9-9f22-6246ea1295f6"
        )


def test_session_id_from_contents_codex():
    """Extract session_id from Codex JSONL format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text('{"payload": {"id": "session-abc-123"}}\n')
        assert Codex.session_id_from_contents(session_file) == "session-abc-123"


def test_session_id_from_contents_gemini():
    """Extract sessionId from Gemini JSON format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.json"
        session_file.write_text(json.dumps({"sessionId": "gemini-session-456"}))
        assert Gemini.session_id_from_contents(session_file) == "gemini-session-456"


def test_parse_spawn_marker_claude_format():
    """Extract spawn marker from Claude JSONL format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text(
            '{"sessionId": "test"}\n'
            '{"type": "user", "message": {"content": "spawn_marker: abc12345\\n\\nYou are..."}}'
        )
        marker = Claude.parse_spawn_marker(session_file)
        assert marker == "abc12345"


def test_parse_spawn_marker_codex_format():
    """Extract spawn marker from Codex JSONL format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text(
            '{"payload": {"id": "test"}}\n'
            '{"payload": {"role": "user", "content": [{"text": "spawn_marker: xyz78901\\n\\nYou are..."}]}}'
        )
        marker = Codex.parse_spawn_marker(session_file)
        assert marker == "xyz78901"


def test_parse_spawn_marker_gemini_native_json_format():
    """Extract spawn marker from Gemini native JSON format."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "session-test.json"
        session_file.write_text(
            json.dumps(
                {
                    "sessionId": "test",
                    "messages": [
                        {"type": "user", "content": "spawn_marker: ghi90123\n\nYou are..."}
                    ],
                }
            )
        )
        marker = Gemini.parse_spawn_marker(session_file)
        assert marker == "ghi90123"


def test_parse_spawn_marker_auto_detects_format():
    """Base parse_spawn_marker auto-detects JSON vs JSONL."""
    with tempfile.TemporaryDirectory() as tmp:
        jsonl_file = Path(tmp) / "test.jsonl"
        jsonl_file.write_text('{"content": "spawn_marker: aaa11111\\n\\nYou are..."}\n')
        assert parse_spawn_marker(jsonl_file) == "aaa11111"

        json_file = Path(tmp) / "test.json"
        json_file.write_text(
            json.dumps(
                {
                    "messages": [
                        {"type": "user", "content": "spawn_marker: bbb22222\n\nYou are..."}
                    ],
                }
            )
        )
        assert parse_spawn_marker(json_file) == "bbb22222"


def test_parse_spawn_marker_returns_none():
    """Return None if no marker found."""
    with tempfile.TemporaryDirectory() as tmp:
        session_file = Path(tmp) / "test.jsonl"
        session_file.write_text('{"id": "test"}\n{"type": "message", "content": "hello"}\n')
        assert parse_spawn_marker(session_file) is None


def test_link_spawn_to_session_updates_db():
    """Verify session_id update to spawns table after sync."""
    with patch("space.os.sessions.sync.ingest") as mock_sync:
        with patch("space.os.sessions.linker.store.ensure") as mock_store:
            mock_conn = MagicMock()
            mock_store.return_value.__enter__.return_value = mock_conn

            linker.link_spawn_to_session("test-spawn-123", "session-456")

            mock_sync.assert_called_once_with(session_id="session-456")

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
            '{"sessionId": "019a4cee-3a32-7e73-93e8-b012b618c274"}\n'
            f'{{"type": "user", "message": {{"content": "spawn_marker: {marker}\\n\\nYou are..."}}}}'
        )

        extracted_marker = Claude.parse_spawn_marker(session_file)
        assert extracted_marker == marker

        session_id = Claude.session_id_from_contents(session_file)
        assert session_id == spawn_id


def test_find_session_for_spawn_integration():
    """Integration test: find_session_for_spawn with marker match."""
    from datetime import datetime, timezone

    from space.lib import paths
    from space.lib.uuid7 import short_id

    spawn_id = "019a4cee-3a32-7e73-93e8-b012b618c274"
    marker = short_id(spawn_id)
    created_at = datetime.now(timezone.utc).isoformat()

    sessions_dir = paths.sessions_dir()
    claude_dir = sessions_dir / "claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    try:
        session_file = claude_dir / f"{spawn_id}.jsonl"
        session_file.write_text(
            f'{{"id": "{spawn_id}"}}\n'
            f'{{"type": "user", "message": {{"content": "spawn_marker: {marker}\\n\\nYou are..."}}}}\n'
        )

        found_session_id = linker.find_session_for_spawn(spawn_id, "claude", created_at)
        assert found_session_id == spawn_id, f"Expected {spawn_id}, got {found_session_id}"
    finally:
        if session_file.exists():
            session_file.unlink()

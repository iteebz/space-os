import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from space.lib import agents, chats


@pytest.fixture
def temp_db():
    """Use temp DB for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        with patch("space.lib.paths.chats_db", return_value=db_path):
            yield db_path


@pytest.fixture
def mock_cli_logs():
    """Create mock CLI log directories with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        claude_dir = tmpdir / ".claude" / "projects" / "test-proj"
        claude_dir.mkdir(parents=True)
        claude_jsonl = claude_dir / "session-1.jsonl"
        claude_jsonl.write_text(
            json.dumps(
                {
                    "type": "user",
                    "message": {"content": "test prompt"},
                    "timestamp": "2025-10-22T10:00:00Z",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": "test response"},
                    "timestamp": "2025-10-22T10:00:05Z",
                }
            )
            + "\n"
        )

        codex_dir = tmpdir / ".codex" / "sessions"
        codex_dir.mkdir(parents=True)
        codex_jsonl = codex_dir / "session-2.jsonl"
        codex_jsonl.write_text(
            json.dumps(
                {
                    "type": "turn_context",
                    "payload": {"model": "codex-model"},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "type": "response_item",
                    "timestamp": "2025-10-22T10:01:00Z",
                    "payload": {
                        "role": "user",
                        "content": [{"type": "text", "text": "codex prompt"}],
                    },
                }
            )
            + "\n"
            + json.dumps(
                {
                    "type": "response_item",
                    "timestamp": "2025-10-22T10:01:05Z",
                    "payload": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "codex response"}],
                    },
                }
            )
            + "\n"
        )

        gemini_dir = tmpdir / ".gemini" / "tmp"
        gemini_dir.mkdir(parents=True)
        gemini_json = gemini_dir / "session-3.json"
        gemini_json.write_text(
            json.dumps(
                {
                    "sessionId": "gemini-1",
                    "messages": [
                        {
                            "role": "user",
                            "content": "gemini prompt",
                            "timestamp": "2025-10-22T10:02:00Z",
                        },
                        {
                            "role": "model",
                            "content": "gemini response",
                            "timestamp": "2025-10-22T10:02:05Z",
                        },
                    ],
                }
            )
        )

        with patch("pathlib.Path.home", return_value=tmpdir):
            yield tmpdir


def test_init_db(temp_db):
    """Test database initialization."""
    with patch("space.lib.paths.chats_db", return_value=temp_db):
        chats.init_db()
        assert temp_db.exists()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "entries" in tables


def test_claude_sessions(mock_cli_logs):
    """Test Claude session ingestion."""
    messages = agents.claude.sessions()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert "test prompt" in messages[0].text


def test_codex_sessions(mock_cli_logs):
    """Test Codex session ingestion."""
    messages = agents.codex.sessions()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert "codex prompt" in messages[0].text


def test_gemini_sessions(mock_cli_logs):
    """Test Gemini session ingestion."""
    messages = agents.gemini.sessions()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert "gemini prompt" in messages[0].text


def test_sync(temp_db, mock_cli_logs):
    """Test sync all CLIs."""
    with patch("space.lib.paths.chats_db", return_value=temp_db):
        chats.init_db()
        results = chats.sync(identity="zealot")

        assert "claude" in results
        assert "codex" in results
        assert "gemini" in results
        assert results["claude"] == 2
        assert results["codex"] == 2
        assert results["gemini"] == 2


def test_search(temp_db):
    """Test search functionality."""
    with patch("space.lib.paths.chats_db", return_value=temp_db):
        chats.init_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO entries (cli, session_id, timestamp, identity, role, text, raw_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "claude",
                "s1",
                "2025-10-22T10:00:00Z",
                "zealot",
                "user",
                "test prompt",
                "hash1",
            ),
        )
        conn.commit()
        conn.close()

        results = chats.search("test")
        assert len(results) == 1

        results = chats.search("test", identity="zealot")
        assert len(results) == 1

        results = chats.search("test", identity="other")
        assert len(results) == 0


def test_list_entries(temp_db):
    """Test listing entries."""
    with patch("space.lib.paths.chats_db", return_value=temp_db):
        chats.init_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        for i in range(3):
            cursor.execute(
                """
                INSERT INTO entries (cli, session_id, timestamp, identity, role, text, raw_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "claude",
                    f"s{i}",
                    f"2025-10-22T10:{i:02d}:00Z",
                    "zealot",
                    "user",
                    f"prompt{i}",
                    f"hash{i}",
                ),
            )
        conn.commit()
        conn.close()

        results = chats.list_entries(identity="zealot")
        assert len(results) == 3

        results = chats.list_entries(identity="other")
        assert len(results) == 0


def test_get_entry(temp_db):
    """Test retrieving a single entry."""
    with patch("space.lib.paths.chats_db", return_value=temp_db):
        chats.init_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO entries (cli, session_id, timestamp, identity, role, text, raw_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "claude",
                "s1",
                "2025-10-22T10:00:00Z",
                "zealot",
                "user",
                "test",
                "hash1",
            ),
        )
        conn.commit()

        cursor.execute("SELECT id FROM entries LIMIT 1")
        entry_id = cursor.fetchone()[0]
        conn.close()

        entry = chats.get_entry(entry_id)
        assert entry is not None
        assert entry["text"] == "test"
        assert entry["identity"] == "zealot"


def test_get_surrounding_context(temp_db):
    """Test retrieving surrounding context."""
    with patch("space.lib.paths.chats_db", return_value=temp_db):
        chats.init_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        for i in range(5):
            cursor.execute(
                """
                INSERT INTO entries (cli, session_id, timestamp, role, text, raw_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "claude",
                    "s1",
                    f"2025-10-22T10:{i:02d}:00Z",
                    "user",
                    f"prompt{i}",
                    f"hash{i}",
                ),
            )
        conn.commit()

        cursor.execute("SELECT id FROM entries WHERE timestamp = '2025-10-22T10:02:00Z'")
        entry_id = cursor.fetchone()[0]
        conn.close()

        context = chats.get_surrounding_context(entry_id)
        assert len(context) > 0
        assert entry_id in [e["id"] for e in context]


def test_unique_constraint(temp_db):
    """Test that duplicates are ignored."""
    with patch("space.lib.paths.chats_db", return_value=temp_db):
        chats.init_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO entries (cli, session_id, timestamp, role, text, raw_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                "claude",
                "s1",
                "2025-10-22T10:00:00Z",
                "user",
                "test",
                "hash1",
            ),
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO entries (cli, session_id, timestamp, role, text, raw_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                "claude",
                "s1",
                "2025-10-22T10:00:00Z",
                "user",
                "test",
                "hash1",
            ),
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM entries")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

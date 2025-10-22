import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sessions import (
    extract_decision,
    get_entry,
    get_surrounding_context,
    init_db,
    list_entries,
    norm_claude_jsonl,
    norm_codex_jsonl,
    norm_gemini_json,
    search,
    sync,
)


@pytest.fixture
def temp_db():
    """Use temp DB for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        with patch("sessions.DB_PATH", db_path):
            yield db_path


def test_init_db(temp_db):
    """Test database initialization."""
    with patch("sessions.DB_PATH", temp_db):
        init_db()
        assert temp_db.exists()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "entries" in tables


def test_norm_claude_jsonl():
    """Test Claude JSONL normalization."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        msg1 = {
            "type": "user",
            "message": {"role": "user", "content": "test prompt"},
            "timestamp": "2025-10-22T10:00:00Z",
            "sessionId": "session-123",
            "cwd": "/tmp",
        }
        msg2 = {
            "type": "assistant",
            "message": {"role": "assistant", "content": "test response"},
            "timestamp": "2025-10-22T10:00:05Z",
            "sessionId": "session-123",
        }
        f.write(json.dumps(msg1) + "\n")
        f.write(json.dumps(msg2) + "\n")
        f.flush()

        messages = norm_claude_jsonl(Path(f.name))
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[0].session_id == Path(f.name).stem

        Path(f.name).unlink()


def test_norm_codex_jsonl():
    """Test Codex JSONL normalization."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        meta = {
            "type": "session_meta",
            "timestamp": "2025-10-22T10:00:00Z",
            "payload": {"cwd": "/workspace"},
        }
        msg1 = {
            "type": "response_item",
            "timestamp": "2025-10-22T10:00:00Z",
            "payload": {"role": "user", "content": [{"type": "input_text", "text": "test prompt"}]},
        }
        msg2 = {
            "type": "response_item",
            "timestamp": "2025-10-22T10:00:05Z",
            "payload": {
                "role": "assistant",
                "content": [{"type": "text", "text": "test response"}],
            },
        }
        f.write(json.dumps(meta) + "\n")
        f.write(json.dumps(msg1) + "\n")
        f.write(json.dumps(msg2) + "\n")
        f.flush()

        messages = norm_codex_jsonl(Path(f.name))
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

        Path(f.name).unlink()


def test_norm_gemini_json():
    """Test Gemini JSON normalization."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        data = {
            "sessionId": "gemini-123",
            "startTime": "2025-10-22T10:00:00Z",
            "messages": [
                {"role": "user", "content": "test prompt", "timestamp": "2025-10-22T10:00:00Z"},
                {"role": "model", "content": "test response", "timestamp": "2025-10-22T10:00:05Z"},
            ],
        }
        json.dump(data, f)
        f.flush()

        messages = norm_gemini_json(Path(f.name))
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[0].session_id == "gemini-123"

        Path(f.name).unlink()


def test_extract_decision():
    """Test decision extraction."""
    prompt = "fix the bug"
    response_dict = {"content": [{"text": "I found the bug. It was in line 42."}]}

    decision, outcome = extract_decision(prompt, response_dict)
    assert decision is not None
    assert "bug" in decision.lower()
    assert outcome == "success"


def test_extract_decision_no_response():
    """Test decision extraction with no response."""
    decision, outcome = extract_decision("prompt", "")
    assert decision is None
    assert outcome == "no_response"


def test_sync(temp_db):
    """Test sync all CLIs."""
    with patch("sessions.DB_PATH", temp_db):
        init_db()
        results = sync(identity="zealot")

        # Should return counts (0 if no actual files)
        assert "claude" in results
        assert "codex" in results
        assert "gemini" in results
        assert isinstance(results["claude"], int)


def test_search(temp_db):
    """Test search functionality."""
    with patch("sessions.DB_PATH", temp_db):
        init_db()

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

        results = search("test")
        assert len(results) == 1

        results = search("test", identity="zealot")
        assert len(results) == 1

        results = search("test", identity="other")
        assert len(results) == 0


def test_list_entries(temp_db):
    """Test listing entries."""
    with patch("sessions.DB_PATH", temp_db):
        init_db()

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

        results = list_entries(identity="zealot")
        assert len(results) == 3

        results = list_entries(identity="other")
        assert len(results) == 0


def test_get_entry(temp_db):
    """Test retrieving a single entry."""
    with patch("sessions.DB_PATH", temp_db):
        init_db()

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

        entry = get_entry(entry_id)
        assert entry is not None
        assert entry["text"] == "test"
        assert entry["identity"] == "zealot"


def test_get_surrounding_context(temp_db):
    """Test retrieving surrounding context."""
    with patch("sessions.DB_PATH", temp_db):
        init_db()

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

        context = get_surrounding_context(entry_id)
        assert len(context) > 0
        assert entry_id in [e["id"] for e in context]


def test_unique_constraint(temp_db):
    """Test that duplicates are ignored."""
    with patch("sessions.DB_PATH", temp_db):
        init_db()

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

        # Try to insert duplicate
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

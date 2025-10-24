"""Security tests for events module SQL injection prevention."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from space.os import events


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


def test_validate_table_accept():
    events._validate_table("events")


def test_validate_table_reject_injection():
    with pytest.raises(ValueError, match="Invalid table"):
        events._validate_table("events; DROP TABLE users")


def test_validate_table_reject_quotes():
    with pytest.raises(ValueError, match="Invalid table"):
        events._validate_table("events' OR '1'='1")


def test_validate_table_reject_unlisted():
    with pytest.raises(ValueError, match="Invalid table"):
        events._validate_table("users")


def test_validate_table_reject_empty():
    with pytest.raises(ValueError, match="Invalid table"):
        events._validate_table("")


def test_add_column_valid(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    events._add_column_if_not_exists(conn, "events", "agent_id", "TEXT")

    cursor = conn.execute("PRAGMA table_info(events)")
    cols = {row[1] for row in cursor.fetchall()}
    assert "agent_id" in cols
    conn.close()


def test_add_column_reject_table_injection(temp_db):
    conn = sqlite3.connect(temp_db)
    with pytest.raises(ValueError, match="Invalid table"):
        events._add_column_if_not_exists(conn, "events; DROP TABLE x", "col", "TEXT")
    conn.close()


def test_add_column_reject_name_injection(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    with pytest.raises(ValueError, match="Invalid column"):
        events._add_column_if_not_exists(conn, "events", "col'; DROP TABLE x", "TEXT")
    conn.close()


def test_add_column_reject_type_injection(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    with pytest.raises(ValueError, match="Invalid column"):
        events._add_column_if_not_exists(conn, "events", "newcol", "TEXT); DROP TABLE x; --")
    conn.close()


def test_add_column_skip_existing(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT, agent_id TEXT)")
    conn.commit()

    events._add_column_if_not_exists(conn, "events", "agent_id", "TEXT")

    cursor = conn.execute("PRAGMA table_info(events)")
    cols = [row[1] for row in cursor.fetchall()]
    assert cols.count("agent_id") == 1
    conn.close()


def test_migrate_add_agent_id(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("""
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            event_type TEXT NOT NULL,
            data TEXT,
            timestamp INTEGER NOT NULL
        )
    """)
    conn.commit()

    events._migrate_add_agent_id(conn)

    cursor = conn.execute("PRAGMA table_info(events)")
    cols = {row[1] for row in cursor.fetchall()}
    assert "agent_id" in cols
    conn.close()


def test_migrate_add_chat_id(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("""
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            event_type TEXT NOT NULL,
            data TEXT,
            timestamp INTEGER NOT NULL
        )
    """)
    conn.commit()

    events._migrate_add_chat_id(conn)

    cursor = conn.execute("PRAGMA table_info(events)")
    cols = {row[1] for row in cursor.fetchall()}
    assert "chat_id" in cols
    conn.close()

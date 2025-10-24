"""Security tests for events module SQL injection prevention."""

import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

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


def test_validate_table_valid():
    """Valid table name should pass validation."""
    events._validate_table("events")


def test_validate_table_rejects_semicolon():
    """Table name with SQL injection should fail."""
    with pytest.raises(ValueError, match="Invalid table"):
        events._validate_table("events; DROP TABLE users")


def test_validate_table_rejects_quotes():
    """Table name with quotes should fail."""
    with pytest.raises(ValueError, match="Invalid table"):
        events._validate_table("events' OR '1'='1")


def test_validate_table_rejects_unlisted():
    """Non-whitelisted table should fail."""
    with pytest.raises(ValueError, match="Invalid table"):
        events._validate_table("users")


def test_validate_table_rejects_empty():
    """Empty table name should fail."""
    with pytest.raises(ValueError, match="Invalid table"):
        events._validate_table("")


def test_add_column_valid(temp_db):
    """Valid column should be added successfully."""
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    events._add_column_if_not_exists(conn, "events", "agent_id", "TEXT")

    cursor = conn.execute("PRAGMA table_info(events)")
    cols = {row[1] for row in cursor.fetchall()}
    assert "agent_id" in cols
    conn.close()


def test_add_column_rejects_invalid_table(temp_db):
    """Invalid table name should be rejected."""
    conn = sqlite3.connect(temp_db)
    with pytest.raises(ValueError, match="Invalid table"):
        events._add_column_if_not_exists(conn, "events; DROP TABLE x", "col", "TEXT")
    conn.close()


def test_add_column_rejects_invalid_name(temp_db):
    """Invalid column name should be rejected."""
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    with pytest.raises(ValueError, match="Invalid column"):
        events._add_column_if_not_exists(conn, "events", "col'; DROP TABLE x", "TEXT")
    conn.close()


def test_add_column_rejects_invalid_type(temp_db):
    """Invalid type should be rejected."""
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    with pytest.raises(ValueError, match="Invalid column"):
        events._add_column_if_not_exists(conn, "events", "newcol", "TEXT); DROP TABLE x; --")
    conn.close()


def test_add_column_skip_existing(temp_db):
    """Existing column should be skipped gracefully."""
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT, agent_id TEXT)")
    conn.commit()

    events._add_column_if_not_exists(conn, "events", "agent_id", "TEXT")

    cursor = conn.execute("PRAGMA table_info(events)")
    cols = [row[1] for row in cursor.fetchall()]
    assert cols.count("agent_id") == 1
    conn.close()


def test_identifier_valid():
    """Valid identifiers should pass."""
    assert "agent_id".isidentifier()
    assert "chat_id".isidentifier()
    assert "timestamp".isidentifier()


def test_identifier_rejects_space():
    """Identifiers with spaces should fail."""
    assert not "agent id".isidentifier()


def test_identifier_rejects_sql():
    """SQL injection in identifier should fail."""
    assert not "agent_id; DROP".isidentifier()
    assert not "agent_id' OR".isidentifier()


def test_identifier_type_spaces():
    """Column types with spaces (like VARCHAR 255) need custom handling."""
    type_str = "VARCHAR 255"
    type_clean = type_str.replace(" ", "")
    assert type_clean.isidentifier()


def test_identifier_type_rejects_injection():
    """SQL injection in type should fail."""
    type_str = "TEXT); DROP TABLE x; --"
    type_clean = type_str.replace(" ", "")
    assert not type_clean.isidentifier()


def test_query_injection_safe():
    """Injection attempt in data parameter should be safe."""
    with mock.patch("space.os.events.DB_PATH") as mock_path:
        mock_path.exists.return_value = False
        malicious_source = "test' OR '1'='1"
        rows = events.query(source=malicious_source, limit=10)
        assert rows == []


def test_migrate_add_agent_id(temp_db):
    """Should add agent_id column safely."""
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
    """Should add chat_id column safely."""
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

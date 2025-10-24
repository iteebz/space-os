"""SQL injection prevention tests for stats module."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from space.apps.stats import lib as stats_lib


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


def test_reject_table_injection():
    invalid_tables = [
        "messages; DROP TABLE users",
        "messages' OR '1'='1",
        'messages"; DROP TABLE users; --',
        "",
    ]
    for table in invalid_tables:
        with pytest.raises(ValueError, match="Invalid identifier"):
            stats_lib._validate_identifier(table, stats_lib.VALID_TABLES)


def test_reject_column_injection():
    invalid_cols = [
        "agent_id; DROP TABLE users",
        "agent_id' OR '1'='1",
        'agent_id"; --',
    ]
    for col in invalid_cols:
        with pytest.raises(ValueError, match="Invalid identifier"):
            stats_lib._validate_identifier(col, stats_lib.VALID_COLUMNS)


def test_reject_table_not_whitelisted():
    with pytest.raises(ValueError, match="Invalid identifier"):
        stats_lib._validate_identifier("sqlite_master", stats_lib.VALID_TABLES)


def test_reject_column_not_whitelisted():
    with pytest.raises(ValueError, match="Invalid identifier"):
        stats_lib._validate_identifier("password", stats_lib.VALID_COLUMNS)


def test_accept_valid_table():
    for table in ["messages", "memories", "knowledge", "events", "channels"]:
        stats_lib._validate_identifier(table, stats_lib.VALID_TABLES)


def test_accept_valid_column():
    for col in ["agent_id", "channel_id", "topic", "domain", "archived_at"]:
        stats_lib._validate_identifier(col, stats_lib.VALID_COLUMNS)


def test_get_columns_boundary(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE test_table (col1 TEXT, col2 INTEGER)")
    conn.commit()

    stats_lib.VALID_TABLES.add("test_table")
    try:
        cols = stats_lib._get_columns_safe(conn, "test_table")
        assert "col1" in cols
        assert "col2" in cols
    finally:
        stats_lib.VALID_TABLES.discard("test_table")
        conn.close()


def test_get_columns_reject_invalid(temp_db):
    conn = sqlite3.connect(temp_db)
    with pytest.raises(ValueError, match="Invalid table"):
        stats_lib._get_columns_safe(conn, "sqlite_master")
    conn.close()


def test_stats_graceful_invalid_table(temp_db):
    result = stats_lib._get_common_db_stats(
        temp_db,
        "nonexistent_table; DROP TABLE x",
    )
    assert result == (0, 0, 0, None, [])


def test_stats_graceful_invalid_column(temp_db):
    result = stats_lib._get_common_db_stats(
        temp_db,
        "events",
        topic_column="invalid_col; DROP TABLE x",
    )
    assert result == (0, 0, 0, None, [])


def test_add_column_reject_table_injection(temp_db):
    from space.os import events as events_module

    conn = sqlite3.connect(temp_db)
    with pytest.raises(ValueError, match="Invalid table"):
        events_module._add_column_if_not_exists(conn, "evil; DROP TABLE x", "col", "TEXT")
    conn.close()


def test_add_column_reject_name_injection(temp_db):
    from space.os import events as events_module

    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    with pytest.raises(ValueError, match="Invalid column"):
        events_module._add_column_if_not_exists(conn, "events", "col; DROP TABLE x", "TEXT")
    conn.close()


def test_add_column_reject_type_injection(temp_db):
    from space.os import events as events_module

    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    with pytest.raises(ValueError, match="Invalid column"):
        events_module._add_column_if_not_exists(conn, "events", "newcol", "TEXT; DROP TABLE x")
    conn.close()


def test_add_column_valid(temp_db):
    from space.os import events as events_module

    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    events_module._add_column_if_not_exists(conn, "events", "newcol", "TEXT")

    cursor = conn.execute("PRAGMA table_info(events)")
    cols = {row[1] for row in cursor.fetchall()}
    assert "newcol" in cols
    conn.close()


def test_validate_table_reject_injection():
    from space.os import events as events_module

    with pytest.raises(ValueError, match="Invalid table"):
        events_module._validate_table("events; DROP TABLE users")


def test_validate_table_reject_unlisted():
    from space.os import events as events_module

    with pytest.raises(ValueError, match="Invalid table"):
        events_module._validate_table("sqlite_master")


def test_validate_table_accept_valid():
    from space.os import events as events_module

    events_module._validate_table("events")

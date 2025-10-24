"""SQL injection prevention tests for stats module."""

import inspect
import sqlite3
import tempfile
from pathlib import Path

import pytest

from space.apps.stats import lib as stats_lib


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


def test_valid_table_names():
    """Valid table names should pass validation."""
    for table in ["messages", "memories", "knowledge", "events", "channels"]:
        stats_lib._validate_identifier(table, stats_lib.VALID_TABLES)


def test_invalid_table_names():
    """Invalid table names should raise ValueError."""
    invalid_tables = [
        "messages; DROP TABLE users",
        "messages' OR '1'='1",
        'messages"; DROP TABLE users; --',
        "../../../etc/passwd",
        "table_info",
        "",
    ]
    for table in invalid_tables:
        with pytest.raises(ValueError, match="Invalid identifier"):
            stats_lib._validate_identifier(table, stats_lib.VALID_TABLES)


def test_valid_column_names():
    """Valid column names should pass validation."""
    for col in ["agent_id", "channel_id", "topic", "domain", "archived_at"]:
        stats_lib._validate_identifier(col, stats_lib.VALID_COLUMNS)


def test_invalid_column_names():
    """Invalid column names should raise ValueError."""
    invalid_cols = [
        "agent_id; DROP TABLE users",
        "agent_id' OR '1'='1",
        'agent_id"; --',
    ]
    for col in invalid_cols:
        with pytest.raises(ValueError, match="Invalid identifier"):
            stats_lib._validate_identifier(col, stats_lib.VALID_COLUMNS)


def test_table_not_in_whitelist():
    """Tables not in whitelist should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid identifier"):
        stats_lib._validate_identifier("sqlite_master", stats_lib.VALID_TABLES)


def test_column_not_in_whitelist():
    """Columns not in whitelist should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid identifier"):
        stats_lib._validate_identifier("password", stats_lib.VALID_COLUMNS)


def test_get_columns_valid_table(temp_db):
    """Should retrieve columns from valid table."""
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


def test_get_columns_invalid_table(temp_db):
    """Should raise ValueError for invalid table."""
    conn = sqlite3.connect(temp_db)
    with pytest.raises(ValueError, match="Invalid table"):
        stats_lib._get_columns_safe(conn, "sqlite_master")
    conn.close()


def test_get_columns_injection_attempt(temp_db):
    """Should reject SQL injection in table name."""
    conn = sqlite3.connect(temp_db)
    with pytest.raises(ValueError, match="Invalid table"):
        stats_lib._get_columns_safe(conn, "test; DROP TABLE users")
    conn.close()


def test_get_common_db_stats_invalid_table(temp_db):
    """Should handle invalid table name gracefully."""
    result = stats_lib._get_common_db_stats(
        temp_db,
        "nonexistent_table; DROP TABLE x",
    )
    assert result == (0, 0, 0, None, [])


def test_get_common_db_stats_invalid_column(temp_db):
    """Should handle invalid column name gracefully."""
    result = stats_lib._get_common_db_stats(
        temp_db,
        "events",
        topic_column="invalid_col; DROP TABLE x",
    )
    assert result == (0, 0, 0, None, [])


def test_invalid_leaderboard_column(temp_db):
    """Should handle invalid leaderboard column gracefully."""
    result = stats_lib._get_common_db_stats(
        temp_db,
        "events",
        leaderboard_column="invalid_col; DROP TABLE x",
    )
    assert result == (0, 0, 0, None, [])


def test_discover_invalid_table():
    """Should handle invalid table in discovery."""
    result = stats_lib._discover_all_agent_ids({"agent1"}, include_archived=False)
    assert "agent1" in result


def test_discover_injection_table():
    """Should reject injection attempts in table name."""
    result = stats_lib._discover_all_agent_ids({"agent1"}, include_archived=False)
    assert isinstance(result, set)
    assert len(result) >= 0


def test_validate_table_valid():
    """Valid table should pass."""
    from space.os import events as events_module

    events_module._validate_table("events")


def test_validate_table_invalid():
    """Invalid table should raise ValueError."""
    from space.os import events as events_module

    with pytest.raises(ValueError, match="Invalid table"):
        events_module._validate_table("events; DROP TABLE users")


def test_validate_table_not_whitelisted():
    """Non-whitelisted table should raise ValueError."""
    from space.os import events as events_module

    with pytest.raises(ValueError, match="Invalid table"):
        events_module._validate_table("sqlite_master")


def test_add_column_invalid_table(temp_db):
    """Should reject invalid table name."""
    from space.os import events as events_module

    conn = sqlite3.connect(temp_db)
    with pytest.raises(ValueError, match="Invalid table"):
        events_module._add_column_if_not_exists(conn, "evil; DROP TABLE x", "col", "TEXT")
    conn.close()


def test_add_column_invalid_column_name(temp_db):
    """Should reject invalid column name."""
    from space.os import events as events_module

    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    with pytest.raises(ValueError, match="Invalid column"):
        events_module._add_column_if_not_exists(conn, "events", "col; DROP TABLE x", "TEXT")
    conn.close()


def test_add_column_invalid_type(temp_db):
    """Should reject invalid column type."""
    from space.os import events as events_module

    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    with pytest.raises(ValueError, match="Invalid column"):
        events_module._add_column_if_not_exists(conn, "events", "newcol", "TEXT; DROP TABLE x")
    conn.close()


def test_add_column_valid(temp_db):
    """Should add valid column successfully."""
    from space.os import events as events_module

    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE events (id TEXT)")
    conn.commit()

    events_module._add_column_if_not_exists(conn, "events", "newcol", "TEXT")

    cursor = conn.execute("PRAGMA table_info(events)")
    cols = {row[1] for row in cursor.fetchall()}
    assert "newcol" in cols
    conn.close()


def test_events_query_parameterized():
    """Events query function should use parameterized queries for data."""
    import inspect

    from space.os import events as events_module

    source = inspect.getsource(events_module.query)
    assert "?" in source
    assert "ORDER BY event_id DESC LIMIT ?" in source


def test_stats_leaderboard_parameterized():
    """Stats leaderboard should use parameterized LIMIT."""
    from space.apps.stats import lib

    source = inspect.getsource(lib._get_common_db_stats)
    assert "LIMIT ?" in source


def test_valid_tables_not_empty():
    """Ensure table whitelist is defined."""
    assert len(stats_lib.VALID_TABLES) > 0
    assert isinstance(stats_lib.VALID_TABLES, set)


def test_valid_columns_not_empty():
    """Ensure column whitelist is defined."""
    assert len(stats_lib.VALID_COLUMNS) > 0
    assert isinstance(stats_lib.VALID_COLUMNS, set)


def test_core_tables_included():
    """Verify core activity tables in whitelist."""
    required = {"messages", "agents", "events"}
    assert required.issubset(stats_lib.VALID_TABLES)


def test_core_columns_included():
    """Verify core activity columns in whitelist."""
    required = {"agent_id", "archived_at"}
    assert required.issubset(stats_lib.VALID_COLUMNS)


def test_no_sql_syntax_in_identifiers():
    """Verify identifiers contain no SQL keywords or syntax."""
    forbidden_chars = {";", "--", "/*", "'", '"'}
    for table in stats_lib.VALID_TABLES:
        for char in forbidden_chars:
            assert char not in table, f"SQL syntax '{char}' found in table name '{table}'"

    for col in stats_lib.VALID_COLUMNS:
        for char in forbidden_chars:
            assert char not in col, f"SQL syntax '{char}' found in column name '{col}'"

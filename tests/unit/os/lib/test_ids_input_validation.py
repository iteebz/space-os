"""Security tests for input validation in SQL ID resolution."""

import pytest

from space.os.lib import ids


def test_invalid_table_rejected():
    """Reject invalid table names."""
    with pytest.raises(ValueError, match="Invalid table"):
        ids.resolve_id("messages'; DROP TABLE messages; --", "agent_id", "abc")


def test_invalid_column_rejected():
    """Reject invalid column names."""
    with pytest.raises(ValueError, match="Invalid column"):
        ids.resolve_id("agents", "agent_id); DROP TABLE agents; --", "abc")


def test_union_select_injection_rejected():
    """Prevent UNION SELECT injection."""
    with pytest.raises(ValueError, match="Invalid"):
        ids.resolve_id("agents' UNION SELECT * FROM agents; --", "agent_id", "x")


def test_comment_escape_injection_rejected():
    """Prevent comment-based escape."""
    with pytest.raises(ValueError, match="Invalid"):
        ids.resolve_id("agents /**/", "agent_id", "x")


def test_stacked_query_injection_rejected():
    """Prevent stacked query injection."""
    with pytest.raises(ValueError, match="Invalid"):
        ids.resolve_id("agents; DELETE FROM agents; --", "agent_id", "x")


def test_case_sensitive_table_validation():
    """Verify table names are case-sensitive."""
    with pytest.raises(ValueError, match="Invalid table"):
        ids.resolve_id("AGENTS", "agent_id", "abc")


def test_case_sensitive_column_validation():
    """Verify column names are case-sensitive."""
    with pytest.raises(ValueError, match="Invalid column"):
        ids.resolve_id("agents", "AGENT_ID", "abc")


def test_empty_table_name_rejected():
    """Reject empty table names."""
    with pytest.raises(ValueError, match="Invalid table"):
        ids.resolve_id("", "agent_id", "abc")


def test_empty_column_name_rejected():
    """Reject empty column names."""
    with pytest.raises(ValueError, match="Invalid column"):
        ids.resolve_id("agents", "", "abc")


def test_whitespace_only_table_rejected():
    """Reject whitespace-only table names."""
    with pytest.raises(ValueError, match="Invalid table"):
        ids.resolve_id("   ", "agent_id", "abc")


def test_whitespace_only_column_rejected():
    """Reject whitespace-only column names."""
    with pytest.raises(ValueError, match="Invalid column"):
        ids.resolve_id("agents", "   ", "abc")


def test_sql_chars_table_rejected():
    """Prevent SQL special characters in table names."""
    injection_attempts = [
        "agents' OR '1'='1",
        "agents`",
        'agents"',
        "agents\\",
        "agents;",
        "agents--",
        "agents/*",
    ]
    for table in injection_attempts:
        with pytest.raises(ValueError, match="Invalid table"):
            ids.resolve_id(table, "agent_id", "abc")


def test_sql_chars_column_rejected():
    """Prevent SQL special characters in column names."""
    injection_attempts = [
        "agent_id' OR '1'='1",
        "agent_id`",
        'agent_id"',
        "agent_id;",
        "agent_id--",
        "agent_id/*",
    ]
    for col in injection_attempts:
        with pytest.raises(ValueError, match="Invalid column"):
            ids.resolve_id("agents", col, "abc")


def test_partial_id_is_safe_parameterized():
    """Verify partial_id parameter is safe (parameterized LIKE)."""
    try:
        ids.resolve_id("agents", "agent_id", "% OR 1=1; --")
    except ValueError as e:
        if "Invalid" in str(e):
            pytest.fail("Partial ID validation should not trigger")


def test_valid_tables_not_empty():
    """Ensure table whitelist exists."""
    assert len(ids._VALID_TABLES) > 0
    assert isinstance(ids._VALID_TABLES, set)


def test_valid_columns_not_empty():
    """Ensure column whitelist exists."""
    assert len(ids._VALID_COLUMNS) > 0
    assert isinstance(ids._VALID_COLUMNS, set)


def test_core_tables_included():
    """Verify core activity tables."""
    required = {"agents", "channels", "messages", "memories"}
    assert required.issubset(ids._VALID_TABLES)


def test_core_id_columns_included():
    """Verify core ID columns."""
    required = {"agent_id", "channel_id", "message_id"}
    assert required.issubset(ids._VALID_COLUMNS)


def test_no_sql_syntax_in_whitelist():
    """Verify identifiers contain no SQL syntax."""
    for table in ids._VALID_TABLES:
        assert ";" not in table and "--" not in table and "/*" not in table
    for col in ids._VALID_COLUMNS:
        assert ";" not in col and "--" not in col and "/*" not in col

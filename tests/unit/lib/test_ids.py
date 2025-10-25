"""Security tests for input validation in SQL ID resolution."""

import pytest

from space.lib import ids


def test_reject_table_injection():
    injections = [
        "messages'; DROP TABLE messages; --",
        "agents' UNION SELECT * FROM agents; --",
        "agents /**/",
        "agents; DELETE FROM agents; --",
    ]
    for table in injections:
        with pytest.raises(ValueError, match="Invalid"):
            ids.resolve_id(table, "agent_id", "abc")


def test_reject_column_injection():
    injections = [
        "agent_id); DROP TABLE agents; --",
        "agent_id) UNION SELECT * FROM agents; --",
    ]
    for col in injections:
        with pytest.raises(ValueError, match="Invalid"):
            ids.resolve_id("agents", col, "abc")


def test_reject_empty_identifiers():
    with pytest.raises(ValueError, match="Invalid table"):
        ids.resolve_id("", "agent_id", "abc")
    with pytest.raises(ValueError, match="Invalid column"):
        ids.resolve_id("agents", "", "abc")


def test_reject_whitespace_only():
    with pytest.raises(ValueError, match="Invalid table"):
        ids.resolve_id("   ", "agent_id", "abc")
    with pytest.raises(ValueError, match="Invalid column"):
        ids.resolve_id("agents", "   ", "abc")


def test_reject_sql_special_chars_table():
    invalid = [
        "agents' OR '1'='1",
        "agents`",
        'agents"',
        "agents\\",
        "agents;",
        "agents--",
        "agents/*",
    ]
    for table in invalid:
        with pytest.raises(ValueError, match="Invalid table"):
            ids.resolve_id(table, "agent_id", "abc")


def test_reject_sql_special_chars_column():
    invalid = [
        "agent_id' OR '1'='1",
        "agent_id`",
        'agent_id"',
        "agent_id;",
        "agent_id--",
        "agent_id/*",
    ]
    for col in invalid:
        with pytest.raises(ValueError, match="Invalid column"):
            ids.resolve_id("agents", col, "abc")


def test_reject_case_mismatch():
    with pytest.raises(ValueError, match="Invalid table"):
        ids.resolve_id("AGENTS", "agent_id", "abc")
    with pytest.raises(ValueError, match="Invalid column"):
        ids.resolve_id("agents", "AGENT_ID", "abc")

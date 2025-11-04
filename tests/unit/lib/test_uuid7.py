"""UUID7 generation, ID resolution, and validation tests."""

import pytest

from space.lib.uuid7 import resolve_id, short_id, uuid7


def test_uuid7_generation():
    """UUID7 generates valid UUIDs."""
    id1 = uuid7()
    id2 = uuid7()

    assert len(id1) == 36
    assert len(id2) == 36
    assert id1 != id2
    assert id1.count("-") == 4


def test_short_id():
    """short_id returns last 8 characters."""
    full_id = "550e8400-e29b-41d4-a716-446655440000"
    assert short_id(full_id) == "55440000"


def test_short_id_consistency():
    """short_id is consistent and collision-resistant."""
    ids = [uuid7() for _ in range(100)]
    short_ids = [short_id(id_) for id_ in ids]

    assert len(short_ids) == len(set(short_ids))


def test_reject_table_injection():
    """Reject SQL injection attempts in table names."""
    injections = [
        "messages'; DROP TABLE messages; --",
        "agents' UNION SELECT * FROM agents; --",
        "agents /**/",
        "agents; DELETE FROM agents; --",
    ]
    for table in injections:
        with pytest.raises(ValueError, match="Invalid"):
            resolve_id(table, "agent_id", "abc")


def test_reject_column_injection():
    """Reject SQL injection attempts in column names."""
    injections = [
        "agent_id); DROP TABLE agents; --",
        "agent_id) UNION SELECT * FROM agents; --",
    ]
    for col in injections:
        with pytest.raises(ValueError, match="Invalid"):
            resolve_id("agents", col, "abc")


def test_reject_empty_identifiers():
    """Reject empty table/column names."""
    with pytest.raises(ValueError, match="Invalid table"):
        resolve_id("", "agent_id", "abc")
    with pytest.raises(ValueError, match="Invalid column"):
        resolve_id("agents", "", "abc")


def test_reject_whitespace_only():
    """Reject whitespace-only identifiers."""
    with pytest.raises(ValueError, match="Invalid table"):
        resolve_id("   ", "agent_id", "abc")
    with pytest.raises(ValueError, match="Invalid column"):
        resolve_id("agents", "   ", "abc")


def test_reject_sql_special_chars_table():
    """Reject special SQL characters in table names."""
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
            resolve_id(table, "agent_id", "abc")


def test_reject_sql_special_chars_column():
    """Reject special SQL characters in column names."""
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
            resolve_id("agents", col, "abc")


def test_reject_case_mismatch():
    """Reject uppercase identifiers (enforce snake_case)."""
    with pytest.raises(ValueError, match="Invalid table"):
        resolve_id("AGENTS", "agent_id", "abc")
    with pytest.raises(ValueError, match="Invalid column"):
        resolve_id("agents", "AGENT_ID", "abc")

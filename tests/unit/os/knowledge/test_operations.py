"""Knowledge operations API tests."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from space.os import knowledge


def make_mock_row(data):
    row = MagicMock()
    row.__getitem__ = lambda self, key: data[key]
    row.keys = lambda: data.keys()
    return row


@pytest.fixture
def mock_db():
    conn = MagicMock()
    with patch("space.lib.store.ensure") as mock_ensure:
        mock_ensure.return_value.__enter__.return_value = conn
        mock_ensure.return_value.__exit__.return_value = None
        yield conn


def test_add_knowledge_inserts_record(mock_db):
    knowledge.add_knowledge("architecture/caching", "agent-1", "content")
    assert mock_db.execute.call_count == 2

    insert_args = mock_db.execute.call_args_list[0][0]
    assert "INSERT INTO knowledge" in insert_args[0]
    assert insert_args[1][1] == "architecture/caching"
    assert insert_args[1][2] == "agent-1"
    assert insert_args[1][3] == "content"

    update_args = mock_db.execute.call_args_list[1][0]
    assert "UPDATE agents SET last_active_at" in update_args[0]
    assert update_args[1][1] == "agent-1"


def test_add_knowledge_returns_id(mock_db):
    result = knowledge.add_knowledge("architecture/caching", "agent-1", "content")
    assert result is not None


def test_list_knowledge_returns_list(mock_db):
    mock_row = make_mock_row(
        {
            "knowledge_id": "k-1",
            "domain": "architecture/caching",
            "agent_id": "a-1",
            "content": "test",
            "created_at": "2024-01-01",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]
    result = knowledge.list_knowledge()
    assert len(result) == 1


def test_list_knowledge_excludes_archived(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.list_knowledge()
    args = mock_db.execute.call_args[0][0]
    assert "archived_at IS NULL" in args


def test_list_knowledge_show_all_includes_archived(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.list_knowledge(show_all=True)
    args = mock_db.execute.call_args[0][0]
    assert "archived_at IS NULL" not in args


def test_query_knowledge_filters_by_domain(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.query_knowledge("architecture/caching")
    args = mock_db.execute.call_args[0]
    assert args[1][0] == "architecture/caching"


def test_query_knowledge_wildcard_support(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.query_knowledge("architecture/*")
    args = mock_db.execute.call_args[0]
    assert "architecture" in args[1][0]


def test_query_knowledge_by_agent_filters(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.query_knowledge_by_agent("a-1")
    args = mock_db.execute.call_args[0]
    assert args[1][0] == "a-1"


def test_get_knowledge_returns_entry(mock_db):
    mock_row = make_mock_row(
        {
            "knowledge_id": "k-1",
            "domain": "architecture/caching",
            "agent_id": "a-1",
            "content": "test",
            "created_at": "2024-01-01",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row
    result = knowledge.get_knowledge("k-1")
    assert result.knowledge_id == "k-1"


def test_get_knowledge_missing_returns_none(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    result = knowledge.get_knowledge("missing")
    assert result is None


def test_archive_knowledge_updates(mock_db):
    knowledge.archive_knowledge("k-1")
    assert mock_db.execute.called


def test_restore_knowledge_clears_timestamp(mock_db):
    knowledge.archive_knowledge("k-1", restore=True)
    assert mock_db.execute.called


def test_get_domain_tree_builds_hierarchy(mock_db):
    mock_rows = [
        ("architecture/caching", "id-1234"),
        ("architecture/auth", "id-5678"),
        ("security/oauth", "id-9abc"),
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_rows

    tree = knowledge.get_domain_tree()
    assert isinstance(tree, dict)


def test_search_uses_fts_and_agent_map(mock_db):
    mock_row = make_mock_row(
        {
            "knowledge_id": "k-1",
            "domain": "architecture/caching",
            "agent_id": "a-1",
            "content": "cache tuning",
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]

    with patch("space.os.spawn.agent_identities", return_value={"a-1": "sentinel"}):
        results = knowledge.search("cache optimizations")

    assert len(results) == 1
    assert results[0].identity == "sentinel"
    sql = mock_db.execute.call_args[0][0]
    assert "knowledge_fts" in sql
    assert "MATCH" in sql


def test_search_falls_back_to_like_when_fts_missing(mock_db):
    fallback_cursor = MagicMock()
    fallback_cursor.fetchall.return_value = []
    mock_db.execute.side_effect = [
        sqlite3.OperationalError("no such table"),
        fallback_cursor,
    ]

    with patch("space.os.spawn.agent_identities", return_value={}):
        knowledge.search("cache")

    like_sql = mock_db.execute.call_args_list[-1][0][0]
    assert "content LIKE" in like_sql

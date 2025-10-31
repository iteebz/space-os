"""Knowledge operations API tests."""

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
    knowledge.api.add_knowledge("architecture/caching", "agent-1", "content")
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
    result = knowledge.api.add_knowledge("architecture/caching", "agent-1", "content")
    assert result is not None


def test_add_knowledge_with_confidence(mock_db):
    knowledge.api.add_knowledge("architecture/caching", "agent-1", "content", confidence=0.95)
    call_args = mock_db.execute.call_args_list[0]
    params = call_args[0][1]
    assert params[4] == 0.95


def test_list_knowledge_returns_list(mock_db):
    mock_row = make_mock_row(
        {
            "knowledge_id": "k-1",
            "domain": "architecture/caching",
            "agent_id": "a-1",
            "content": "test",
            "confidence": 0.9,
            "created_at": "2024-01-01",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]
    result = knowledge.api.list_knowledge()
    assert len(result) == 1


def test_list_knowledge_excludes_archived(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.api.list_knowledge()
    args = mock_db.execute.call_args[0][0]
    assert "archived_at IS NULL" in args


def test_list_knowledge_show_all_includes_archived(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.api.list_knowledge(show_all=True)
    args = mock_db.execute.call_args[0][0]
    assert "archived_at IS NULL" not in args


def test_query_knowledge_filters_by_domain(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.api.query_knowledge("architecture/caching")
    args = mock_db.execute.call_args[0]
    assert args[1][0] == "architecture/caching"


def test_query_knowledge_wildcard_support(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.api.query_knowledge("architecture/*")
    args = mock_db.execute.call_args[0]
    assert "architecture" in args[1][0]


def test_query_knowledge_by_agent_filters(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.api.query_knowledge_by_agent("a-1")
    args = mock_db.execute.call_args[0]
    assert args[1][0] == "a-1"


def test_get_knowledge_returns_entry(mock_db):
    mock_row = make_mock_row(
        {
            "knowledge_id": "k-1",
            "domain": "architecture/caching",
            "agent_id": "a-1",
            "content": "test",
            "confidence": 0.9,
            "created_at": "2024-01-01",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row
    result = knowledge.api.get_knowledge("k-1")
    assert result.knowledge_id == "k-1"


def test_get_knowledge_missing_returns_none(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    result = knowledge.api.get_knowledge("missing")
    assert result is None


def test_archive_knowledge_updates(mock_db):
    knowledge.api.archive_knowledge("k-1")
    assert mock_db.execute.called


def test_restore_knowledge_clears_timestamp(mock_db):
    knowledge.api.archive_knowledge("k-1", restore=True)
    assert mock_db.execute.called


def test_find_related_knowledge_returns_scores(mock_db):
    related_row = make_mock_row(
        {
            "knowledge_id": "k-2",
            "domain": "architecture/caching/redis",
            "agent_id": "a-1",
            "content": "Redis LRU eviction policy",
            "confidence": 0.8,
            "created_at": "2024-01-02",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [related_row]

    from space.core.models import Knowledge

    entry = Knowledge(
        knowledge_id="k-1",
        domain="architecture/caching",
        agent_id="a-1",
        content="caching strategy Redis",
        confidence=0.9,
        created_at="2024-01-01",
        archived_at=None,
    )
    result = knowledge.api.find_related_knowledge(entry)
    assert len(result) > 0
    assert isinstance(result[0], tuple)


def test_get_domain_tree_builds_hierarchy(mock_db):
    domains = ["architecture/caching", "architecture/auth", "security/oauth"]
    mock_rows = []
    for domain in domains:
        row = MagicMock()
        row.__getitem__ = lambda s, k, d=domain: d if k == 0 else None
        mock_rows.append(row)
    mock_db.execute.return_value.fetchall.return_value = mock_rows

    tree = knowledge.api.get_domain_tree()
    assert isinstance(tree, dict)

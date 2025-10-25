"""Knowledge entries API contract tests."""

from unittest.mock import MagicMock, patch

import pytest

from space.core import knowledge


def make_mock_row(data):
    row = MagicMock()
    row.__getitem__ = lambda self, key: data[key]
    row.keys = lambda: data.keys()
    return row


@pytest.fixture
def mock_db():
    conn = MagicMock()
    with patch("space.lib.db.ensure") as mock_ensure:
        mock_ensure.return_value.__enter__.return_value = conn
        mock_ensure.return_value.__exit__.return_value = None
        yield conn


def test_add_entry_inserts_record(mock_db):
    knowledge.add_entry("ml", "agent-1", "content")
    assert mock_db.execute.called


def test_add_entry_returns_id(mock_db):
    result = knowledge.add_entry("ml", "agent-1", "content")
    assert result is not None


def test_add_entry_with_confidence(mock_db):
    knowledge.add_entry("ml", "agent-1", "content", confidence=0.95)
    call_args = mock_db.execute.call_args_list[1]
    params = call_args[0][1]
    assert params[4] == 0.95


def test_list_entries_returns_list(mock_db):
    mock_row = make_mock_row(
        {
            "knowledge_id": "k-1",
            "domain": "ml",
            "agent_id": "a-1",
            "content": "test",
            "confidence": 0.9,
            "created_at": "2024-01-01",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]
    result = knowledge.list_entries()
    assert len(result) == 1


def test_list_entries_excludes_archived(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.list_entries()
    args = mock_db.execute.call_args[0][0]
    assert "archived_at IS NULL" in args


def test_list_entries_show_all_includes_archived(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.list_entries(show_all=True)
    args = mock_db.execute.call_args[0][0]
    assert "archived_at IS NULL" not in args


def test_query_by_domain_filters(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.query_by_domain("ml")
    args = mock_db.execute.call_args[0]
    assert args[1][0] == "ml"


def test_query_by_agent_filters(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    knowledge.query_by_agent("a-1")
    args = mock_db.execute.call_args[0]
    assert args[1][0] == "a-1"


def test_get_by_id_returns_entry(mock_db):
    mock_row = make_mock_row(
        {
            "knowledge_id": "k-1",
            "domain": "ml",
            "agent_id": "a-1",
            "content": "test",
            "confidence": 0.9,
            "created_at": "2024-01-01",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row
    result = knowledge.get_by_id("k-1")
    assert result.knowledge_id == "k-1"


def test_get_by_id_missing_returns_none(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    result = knowledge.get_by_id("missing")
    assert result is None


def test_archive_entry_updates(mock_db):
    knowledge.archive_entry("k-1")
    assert mock_db.execute.called


def test_restore_entry_clears_timestamp(mock_db):
    knowledge.restore_entry("k-1")
    assert mock_db.execute.called


def test_find_related_returns_scores(mock_db):
    make_mock_row(
        {
            "knowledge_id": "k-1",
            "domain": "ml",
            "agent_id": "a-1",
            "content": "neural networks deep learning",
            "confidence": 0.9,
            "created_at": "2024-01-01",
            "archived_at": None,
        }
    )
    related_row = make_mock_row(
        {
            "knowledge_id": "k-2",
            "domain": "ai",
            "agent_id": "a-1",
            "content": "deep learning models",
            "confidence": 0.8,
            "created_at": "2024-01-02",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [related_row]

    from space.core.models import Knowledge

    entry = Knowledge(
        knowledge_id="k-1",
        domain="ml",
        agent_id="a-1",
        content="neural networks deep learning",
        confidence=0.9,
        created_at="2024-01-01",
        archived_at=None,
    )
    result = knowledge.find_related(entry)
    assert len(result) > 0
    assert isinstance(result[0], tuple)


def test_search_returns_structured_results(mock_db):
    with patch("space.core.spawn.resolve_agent") as mock_agent:
        mock_agent.return_value = MagicMock(agent_id="a-1", name="agent1")
        mock_row = make_mock_row(
            {
                "knowledge_id": "k-1",
                "domain": "ml",
                "agent_id": "a-1",
                "content": "test",
                "created_at": "2024-01-01",
            }
        )
        mock_db.execute.return_value.fetchall.return_value = [mock_row]
        result = knowledge.search("test", None, True)
        assert len(result) == 1
        assert result[0]["source"] == "knowledge"


def test_search_filters_by_identity(mock_db):
    with patch("space.core.spawn.resolve_agent") as mock_agent:
        mock_agent.return_value = MagicMock(agent_id="a-1", name="agent1")
        mock_db.execute.return_value.fetchall.return_value = []
        knowledge.search("test", "agent1", False)
        args = mock_db.execute.call_args[0]
        assert "AND agent_id = ?" in args[0]

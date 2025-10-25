"""Spawn agents API contract tests."""

from unittest.mock import MagicMock, patch

import pytest

from space.core import spawn


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


def test_resolve_agent_finds_by_name(mock_db):
    mock_row = make_mock_row(
        {
            "agent_id": "a-1",
            "name": "agent1",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row

    result = spawn.resolve_agent("agent1")
    assert result.agent_id == "a-1"


def test_resolve_agent_finds_by_id(mock_db):
    mock_row = make_mock_row(
        {
            "agent_id": "a-1",
            "name": "agent1",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row

    result = spawn.resolve_agent("a-1")
    assert result.identity == "agent1"


def test_resolve_agent_missing_returns_none(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    result = spawn.resolve_agent("missing")
    assert result is None


def test_ensure_agent_creates_new(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    with patch("space.core.spawn.api.agents.uuid.uuid4") as mock_uuid:
        mock_uuid.return_value = "a-1"
        result = spawn.ensure_agent("newagent")
    assert result is not None


def test_ensure_agent_returns_existing(mock_db):
    mock_row = make_mock_row(
        {
            "agent_id": "a-1",
            "name": "agent1",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row

    result = spawn.ensure_agent("agent1")
    assert result == "a-1"


def test_describe_self_updates(mock_db):
    mock_db.execute.return_value.fetchone.return_value = make_mock_row({"agent_id": "a-1"})
    spawn.describe_self("agent1", "I am agent1")
    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("UPDATE agents SET self_description" in call for call in calls)


def test_describe_self_creates_if_missing(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    spawn.describe_self("newagent", "description")
    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("INSERT INTO agents" in call for call in calls)


def test_rename_agent_updates(mock_db):
    mock_row = make_mock_row(
        {
            "agent_id": "a-1",
            "name": "old",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row
    mock_db.execute.return_value.fetchone.side_effect = [mock_row, None]

    result = spawn.rename_agent("old", "new")
    assert result is True


def test_rename_agent_missing_returns_false(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    result = spawn.rename_agent("old", "new")
    assert result is False


def test_archive_agent_updates(mock_db):
    mock_row = make_mock_row(
        {
            "agent_id": "a-1",
            "name": "agent1",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row

    result = spawn.archive_agent("agent1")
    assert result is True


def test_archive_agent_missing_returns_false(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    result = spawn.archive_agent("missing")
    assert result is False


def test_unarchive_agent_updates(mock_db):
    mock_db.execute.return_value.fetchone.return_value = make_mock_row({"agent_id": "a-1"})
    result = spawn.unarchive_agent("agent1")
    assert result is True


def test_unarchive_agent_missing_returns_false(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    result = spawn.unarchive_agent("missing")
    assert result is False


def test_list_agents_returns_list(mock_db):
    mock_row1 = make_mock_row({"identity": "agent1"})
    mock_row2 = make_mock_row({"identity": "agent2"})
    mock_db.execute.return_value.fetchall.return_value = [mock_row1, mock_row2]

    result = spawn.list_agents()
    assert len(result) == 2
    assert "agent1" in result


def test_merge_agents_updates_all_dbs(mock_db):
    mock_from = make_mock_row(
        {
            "agent_id": "a-1",
            "name": "from",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_to = make_mock_row(
        {
            "agent_id": "a-2",
            "name": "to",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchone.side_effect = [mock_from, mock_to]

    with patch("space.lib.paths.space_data") as mock_paths:
        from pathlib import Path

        mock_paths.return_value = Path("/tmp")
        result = spawn.merge_agents("from", "to")

    assert result is True

from unittest.mock import MagicMock, patch

import pytest

from space.core.models import Agent
from space.os import spawn


def make_mock_row(data):
    row = MagicMock()
    row.__getitem__ = lambda self, key: data[key]
    row.keys = lambda: data.keys()
    return row


def test_get_agent_finds_by_identity(mock_db):
    mock_row = make_mock_row(
        {
            "agent_id": "a-1",
            "identity": "agent1",
            "constitution": "c.md",
            "model": "claude-haiku-4-5",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row

    result = spawn.get_agent("agent1")
    assert result.agent_id == "a-1"
    assert result.identity == "agent1"
    assert result.constitution == "c.md"
    assert result.provider == "claude"
    assert result.model == "claude-haiku-4-5"


def test_get_agent_finds_by_id(mock_db):
    mock_row = make_mock_row(
        {
            "agent_id": "a-1",
            "identity": "agent1",
            "constitution": "c.md",
            "model": "claude-haiku-4-5",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row

    result = spawn.get_agent("a-1")
    assert result.identity == "agent1"


def test_get_agent_missing_returns_none(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    result = spawn.get_agent("missing")
    assert result is None


def test_register_agent_success(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None  # Agent not found
    with patch("space.os.spawn.api.agents.uuid.uuid4") as mock_uuid:
        mock_uuid.return_value = "new-uuid"
        agent_id = spawn.register_agent("newagent", "claude-haiku-4-5", "c.md")

    assert agent_id == "new-uuid"
    # Check that the agents table was called (not the events table)
    calls = mock_db.execute.call_args_list
    agents_call = next((call for call in calls if "INSERT INTO agents" in call[0][0]), None)
    assert agents_call is not None
    assert (
        "INSERT INTO agents (agent_id, identity, constitution, model, role, created_at) VALUES (?, ?, ?, ?, ?, ?)"
        in agents_call[0][0]
    )
    assert agents_call[0][1] == (
        "new-uuid",
        "newagent",
        "c.md",
        "claude-haiku-4-5",
        None,
        agents_call[0][1][5],
    )


def test_register_agent_already_exists(mock_db):
    mock_row = make_mock_row(
        {
            "agent_id": "a-1",
            "identity": "agent1",
            "constitution": "c.md",
            "model": "claude-haiku-4-5",
            "self_description": None,
            "archived_at": None,
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row  # Agent found

    with pytest.raises(ValueError, match="Identity 'agent1' already registered"):
        spawn.register_agent("agent1", "claude-haiku-4-5", "c.md")


def test_rename_agent_updates(mock_db):
    mock_old_agent = Agent(
        agent_id="a-1",
        identity="old",
        constitution="c.md",
        model="claude-haiku-4-5",
        spawn_count=0,
        created_at="2024-01-01",
    )
    with patch("space.os.spawn.api.agents.get_agent") as mock_get_agent:
        mock_get_agent.side_effect = [mock_old_agent, None]  # old exists, new doesn't
        result = spawn.rename_agent("old", "new")
    assert result is True
    mock_db.execute.assert_called_with(
        "UPDATE agents SET identity = ? WHERE agent_id = ?", ("new", "a-1")
    )


def test_rename_agent_missing_returns_false(mock_db):
    with patch("space.os.spawn.api.agents.get_agent", return_value=None):
        result = spawn.rename_agent("old", "new")
        assert result is False


def test_rename_agent_new_exists_returns_false(mock_db):
    mock_old_agent = Agent(
        agent_id="a-1",
        identity="old",
        constitution="c.md",
        model="claude-haiku-4-5",
        spawn_count=0,
        created_at="2024-01-01",
    )
    mock_new_agent = Agent(
        agent_id="a-2",
        identity="new",
        constitution="c.md",
        model="claude-haiku-4-5",
        spawn_count=0,
        created_at="2024-01-01",
    )
    with patch("space.os.spawn.api.agents.get_agent") as mock_get_agent:
        mock_get_agent.side_effect = [mock_old_agent, mock_new_agent]
        result = spawn.rename_agent("old", "new")
        assert result is False


def test_archive_agent_updates(mock_db):
    mock_agent = Agent(
        agent_id="a-1",
        identity="agent1",
        constitution="c.md",
        model="claude-haiku-4-5",
        spawn_count=0,
        created_at="2024-01-01",
    )
    with patch("space.os.spawn.api.agents.get_agent", return_value=mock_agent):
        result = spawn.archive_agent("agent1")
        assert result is True
        mock_db.execute.assert_called_with(
            "UPDATE agents SET archived_at = ? WHERE agent_id = ?",
            (mock_db.execute.call_args[0][1][0], "a-1"),
        )


def test_archive_agent_missing_returns_false(mock_db):
    with patch("space.os.spawn.api.agents.get_agent", return_value=None):
        result = spawn.archive_agent("missing")
        assert result is False


def test_unarchive_agent_updates(mock_db):
    mock_db.execute.return_value.fetchone.return_value = make_mock_row({"agent_id": "a-1"})
    result = spawn.unarchive_agent("agent1")
    assert result is True
    mock_db.execute.assert_called_with(
        "UPDATE agents SET archived_at = NULL WHERE agent_id = ?", ("a-1",)
    )


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
    mock_from = Agent(
        agent_id="a-1",
        identity="from",
        constitution="c.md",
        model="claude-haiku-4-5",
        spawn_count=0,
        created_at="2024-01-01",
    )
    mock_to = Agent(
        agent_id="a-2",
        identity="to",
        constitution="c.md",
        model="claude-haiku-4-5",
        spawn_count=0,
        created_at="2024-01-01",
    )
    with patch("space.os.spawn.api.agents.get_agent") as mock_get_agent:
        mock_get_agent.side_effect = [mock_from, mock_to]
        with patch("space.lib.paths.space_data") as mock_paths:
            from pathlib import Path

            mock_paths.return_value = Path("/tmp")
            result = spawn.merge_agents("from", "to")

    assert result is True


def test_register_agent_rejects_spaces(mock_db):
    with pytest.raises(ValueError, match="Identity cannot contain spaces"):
        spawn.register_agent("my agent", "claude-haiku-4-5", "c.md")


def test_register_agent_suggests_hyphen(mock_db):
    with pytest.raises(ValueError, match="Use hyphens instead: 'my-agent'"):
        spawn.register_agent("my agent", "claude-haiku-4-5", "c.md")


def test_rename_agent_rejects_spaces(mock_db):
    mock_agent = Agent(
        agent_id="a-1",
        identity="old",
        constitution="c.md",
        model="claude-haiku-4-5",
        spawn_count=0,
        created_at="2024-01-01",
    )
    with patch("space.os.spawn.api.agents.get_agent", return_value=mock_agent):
        with pytest.raises(ValueError, match="Identity cannot contain spaces"):
            spawn.rename_agent("old", "new name")


def test_clone_agent_rejects_spaces(mock_db):
    mock_agent = Agent(
        agent_id="a-1",
        identity="original",
        constitution="c.md",
        model="claude-haiku-4-5",
        spawn_count=0,
        created_at="2024-01-01",
    )
    with patch("space.os.spawn.api.agents.get_agent", return_value=mock_agent):
        with pytest.raises(ValueError, match="Identity cannot contain spaces"):
            spawn.clone_agent("original", "new agent")

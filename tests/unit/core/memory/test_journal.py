"""Memory journal topic tests - sleep journal persists with #journal topic."""

from unittest.mock import MagicMock, patch

import pytest

from space.core import memory


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


def test_list_journal_entries(mock_db):
    mock_row = make_mock_row(
        {
            "memory_id": "m-1",
            "agent_id": "a-1",
            "topic": "journal",
            "message": "sleep state",
            "timestamp": "2024-01-01",
            "created_at": 1234567890,
            "archived_at": None,
            "core": 0,
            "source": "manual",
            "bridge_channel": None,
            "code_anchors": None,
            "synthesis_note": None,
            "supersedes": None,
            "superseded_by": None,
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]

    with patch("space.core.spawn.get_agent") as mock_agent:
        mock_agent.return_value = MagicMock(agent_id="a-1")
        result = memory.list_entries("agent1", topic="journal", limit=1)
        assert len(result) == 1
        assert result[0].topic == "journal"


def test_add_journal_entry(mock_db):
    memory.add_entry("a-1", "journal", "sleep handoff complete")
    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("INSERT INTO memories" in call for call in calls)


def test_replace_journal_entry(mock_db):
    with patch("space.core.memory.api.entries.resolve_id") as mock_resolve:
        mock_resolve.return_value = "m-1"
        memory.replace_entry(["m-1"], "a-1", "journal", "updated sleep state")
        calls = [call[0][0] for call in mock_db.execute.call_args_list]
        assert any("INSERT INTO memories" in call for call in calls)

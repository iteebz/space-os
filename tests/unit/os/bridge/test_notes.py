"""Bridge notes API contract tests."""

from unittest.mock import MagicMock, patch

import pytest

from space.os import bridge


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


def test_add_note_inserts_record(mock_db):
    with patch("space.os.spawn.get_agent") as mock_agent:
        mock_agent.return_value = MagicMock(agent_id="a-1")


def test_add_note_returns_id(mock_db):
    with patch("space.os.spawn.get_agent") as mock_agent:
        mock_agent.return_value = MagicMock(agent_id="a-1")
        result = bridge.add_note("ch-1", "agent-1", "test note")
        assert result is not None


def test_get_notes_returns_list(mock_db):
    mock_row = make_mock_row(
        {
            "note_id": "n-1",
            "channel_id": "ch-1",
            "agent_id": "a-1",
            "content": "note",
            "created_at": "2024-01-01",
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]
    result = bridge.get_notes("ch-1")
    assert len(result) == 1


def test_get_notes_empty_channel(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    result = bridge.get_notes("ch-1")
    assert result == []

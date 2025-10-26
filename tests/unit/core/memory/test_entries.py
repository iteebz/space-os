"""Memory entries API contract tests."""

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


@pytest.fixture
def mock_get_agent():
    with patch("space.core.spawn.get_agent") as mock:
        mock.return_value = MagicMock(agent_id="test-agent-id")
        yield mock


def test_add_entry_creates_record(mock_db):
    memory.add_entry("agent-123", "topic-x", "test message")

    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    mem_call = [call for call in calls if "INSERT INTO memories" in call][0]
    assert "INSERT INTO memories" in mem_call


def test_add_entry_with_core_flag(mock_db):
    memory.add_entry("agent-123", "topic", "message", core=True)

    calls = [
        call[0] for call in mock_db.execute.call_args_list if "INSERT INTO memories" in call[0][0]
    ]
    assert calls
    args = calls[0][1]
    assert args[6] == 1


def test_add_entry_returns_id(mock_db):
    result = memory.add_entry("agent-123", "topic", "message")
    assert result is not None


def test_list_entries_basic(mock_db, mock_get_agent):
    mock_row = make_mock_row(
        {
            "memory_id": "m-1",
            "agent_id": "agent-123",
            "topic": "t1",
            "message": "msg1",
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

    result = memory.list_entries("agent-123")
    assert len(result) == 1


def test_list_entries_with_topic_filter(mock_db, mock_get_agent):
    mock_db.execute.return_value.fetchall.return_value = []

    memory.list_entries("test-agent-id", topic="insights")

    args = mock_db.execute.call_args[0]
    assert "AND topic = ?" in args[0]


def test_list_entries_with_core_filter(mock_db, mock_get_agent):
    mock_db.execute.return_value.fetchall.return_value = []

    memory.list_entries("test-agent-id", filter="core")

    args = mock_db.execute.call_args[0]
    assert "AND core = 1" in args[0]


def test_list_entries_excludes_archived_by_default(mock_db, mock_get_agent):
    mock_db.execute.return_value.fetchall.return_value = []

    memory.list_entries("test-agent-id")

    args = mock_db.execute.call_args[0]
    assert "AND archived_at IS NULL" in args[0]


def test_list_entries_shows_all_when_requested(mock_db, mock_get_agent):
    mock_db.execute.return_value.fetchall.return_value = []

    memory.list_entries("test-agent-id", show_all=True)

    args = mock_db.execute.call_args[0]
    assert "AND archived_at IS NULL" not in args[0]


def test_list_entries_agent_not_found_raises(mock_get_agent):
    mock_get_agent.return_value = None

    with pytest.raises(ValueError, match="not found"):
        memory.list_entries("nonexistent")


def test_replace_entry_archives_old(mock_db):
    with patch("space.core.memory.api.entries.resolve_id", return_value="m-1"):
        memory.replace_entry(["m-1"], "agent-123", "topic", "new msg")

    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("UPDATE memories SET archived_at" in call for call in calls)


def test_replace_entry_creates_new(mock_db):
    with patch("space.core.memory.api.entries.resolve_id", return_value="m-1"):
        memory.replace_entry(["m-1"], "agent-123", "topic", "new msg")

    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("INSERT INTO memories" in call for call in calls)


def test_replace_entry_returns_id(mock_db):
    with patch("space.core.memory.api.entries.resolve_id", return_value="m-1"):
        result = memory.replace_entry(["m-1"], "agent-123", "topic", "new msg")
    assert result is not None

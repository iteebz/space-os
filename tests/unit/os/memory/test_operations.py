"""Memory operations API tests."""

from unittest.mock import MagicMock, patch

import pytest

from space.os import memory


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
    with patch("space.os.spawn.get_agent") as mock:
        mock.return_value = MagicMock(agent_id="test-agent-id")
        yield mock


def test_add_memory_creates_record(mock_db):
    memory.api.add_memory("agent-123", "test message", topic="observations")

    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    mem_call = [call for call in calls if "INSERT INTO memories" in call][0]
    assert "INSERT INTO memories" in mem_call


def test_add_memory_with_core_flag(mock_db):
    memory.api.add_memory("agent-123", "message", core=True)

    calls = [
        call[0] for call in mock_db.execute.call_args_list if "INSERT INTO memories" in call[0][0]
    ]
    assert calls
    args = calls[0][1]
    assert args[5] == 1


def test_add_memory_returns_id(mock_db):
    result = memory.api.add_memory("agent-123", "test message")
    assert result is not None


def test_list_memories_basic(mock_db, mock_get_agent):
    mock_row = make_mock_row(
        {
            "memory_id": "m-1",
            "agent_id": "agent-123",
            "topic": "observations",
            "message": "msg1",
            "created_at": "2024-01-01T12:00:00",
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

    result = memory.api.list_memories("agent-123")
    assert len(result) == 1


def test_list_memories_with_topic_filter(mock_db, mock_get_agent):
    mock_db.execute.return_value.fetchall.return_value = []

    memory.api.list_memories("test-agent-id", topic="observations")

    args = mock_db.execute.call_args[0]
    assert "AND topic = ?" in args[0]


def test_list_memories_with_core_filter(mock_db, mock_get_agent):
    mock_db.execute.return_value.fetchall.return_value = []

    memory.api.list_memories("test-agent-id", filter_type="core")

    args = mock_db.execute.call_args[0]
    assert "AND core = 1" in args[0]


def test_list_memories_excludes_archived_by_default(mock_db, mock_get_agent):
    mock_db.execute.return_value.fetchall.return_value = []

    memory.api.list_memories("test-agent-id")

    args = mock_db.execute.call_args[0]
    assert "AND archived_at IS NULL" in args[0]


def test_list_memories_shows_all_when_requested(mock_db, mock_get_agent):
    mock_db.execute.return_value.fetchall.return_value = []

    memory.api.list_memories("test-agent-id", show_all=True)

    args = mock_db.execute.call_args[0]
    assert "AND archived_at IS NULL" not in args[0]


def test_list_memories_agent_not_found_raises(mock_get_agent):
    mock_get_agent.return_value = None

    with pytest.raises(ValueError, match="not found"):
        memory.api.list_memories("nonexistent")


def test_get_memory_returns_entry(mock_db):
    mock_row = make_mock_row(
        {
            "memory_id": "m-1",
            "agent_id": "agent-123",
            "topic": "observations",
            "message": "test msg",
            "created_at": "2024-01-01T12:00:00",
            "archived_at": None,
            "core": 1,
            "source": "manual",
            "bridge_channel": None,
            "code_anchors": None,
            "synthesis_note": None,
            "supersedes": None,
            "superseded_by": None,
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row

    with patch("space.lib.uuid7.resolve_id") as mock_resolve:
        mock_resolve.return_value = "m-1"
        result = memory.api.get_memory("m-1")
        assert result is not None
        assert result.memory_id == "m-1"


def test_get_memory_not_found_returns_none(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None

    with patch("space.lib.uuid7.resolve_id") as mock_resolve:
        mock_resolve.return_value = "m-notfound"
        result = memory.api.get_memory("m-notfound")
        assert result is None


def test_toggle_memory_core_flips_state(mock_db):
    mock_row = make_mock_row(
        {
            "memory_id": "m-1",
            "agent_id": "agent-123",
            "topic": "observations",
            "message": "test",
            "created_at": "2024-01-01T12:00:00",
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
    mock_db.execute.return_value.fetchone.return_value = mock_row

    with patch("space.lib.uuid7.resolve_id"):
        result = memory.api.toggle_memory_core("m-1")
        assert result is True


def test_archive_memory_sets_timestamp(mock_db):
    mock_row = make_mock_row(
        {
            "memory_id": "m-1",
            "agent_id": "agent-123",
            "topic": "observations",
            "message": "test",
            "created_at": "2024-01-01T12:00:00",
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
    mock_db.execute.return_value.fetchone.return_value = mock_row

    with patch("space.lib.uuid7.resolve_id") as mock_resolve:
        mock_resolve.return_value = "m-1"
        with patch("space.os.memory.api.operations.get_memory") as mock_get:
            from space.core.models import Memory

            mock_get.return_value = Memory(
                memory_id="m-1",
                agent_id="agent-123",
                message="test",
                topic="observations",
                created_at="2024-01-01T12:00:00",
                archived_at=None,
                core=False,
                source="manual",
            )
            memory.api.archive_memory("m-1")
            calls = [call for call in mock_db.execute.call_args_list if "archived_at" in call[0][0]]
            assert any("UPDATE memories SET archived_at = ?" in call[0][0] for call in calls)

"""Spawn tasks API contract tests."""

from unittest.mock import MagicMock, patch

import pytest

from space.core.models import Session, TaskStatus
from space.os import spawn


def make_mock_row(data):
    row = MagicMock()
    row.__getitem__ = lambda self, key: data[key]
    row.keys = lambda: data.keys()
    return row


@pytest.fixture
def mock_resolve_agent():
    with patch("space.os.spawn.api.tasks.get_agent") as mock:
        mock.return_value = MagicMock(agent_id="agent-123")
        yield mock


def test_create_task_returns_session(mock_db, mock_resolve_agent):
    mock_session = Session(
        id="task-123",
        agent_id="agent-123",
        spawn_number=1,
        status=TaskStatus.PENDING,
        is_task=True,
    )
    with patch("space.os.spawn.api.tasks.create_session", return_value=mock_session):
        result = spawn.create_task(identity="test-role")
        assert result == mock_session
        assert result.is_task is True


def test_create_task_with_channel_id(mock_resolve_agent):
    mock_session = Session(
        id="task-123",
        agent_id="agent-123",
        spawn_number=1,
        status=TaskStatus.PENDING,
        is_task=True,
        channel_id="ch-123",
    )
    with patch("space.os.spawn.api.tasks.create_session", return_value=mock_session) as mock_create:
        spawn.create_task(identity="test-role", channel_id="ch-123")
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs.get("channel_id") == "ch-123"


def test_create_task_unknown_role_raises(mock_resolve_agent):
    mock_resolve_agent.return_value = None

    with pytest.raises(ValueError, match="not found"):
        spawn.create_task(identity="unknown")


def test_get_task_returns_session(mock_db):
    mock_row = make_mock_row(
        {
            "id": "t-1",
            "agent_id": "a-1",
            "spawn_number": 1,
            "channel_id": None,
            "status": "pending",
            "is_task": True,
            "constitution_hash": None,
            "pid": None,
            "created_at": "2024-01-01T00:00:00",
            "ended_at": None,
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row

    result = spawn.get_task("t-1")
    assert result is not None
    assert result.id == "t-1"
    assert result.is_task is True


def test_get_task_missing_returns_none(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None

    result = spawn.get_task("missing")
    assert result is None


def test_start_task_updates_status(mock_db):
    spawn.start_task("t-1")

    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("UPDATE sessions SET" in call for call in calls)


def test_start_task_sets_running(mock_db):
    spawn.start_task("t-1")

    args = [call[0][1] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]][0]
    assert TaskStatus.RUNNING.value in args


def test_start_task_with_pid(mock_db):
    spawn.start_task("t-1", pid=12345)

    args = [call[0][1] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]][0]
    assert 12345 in args


def test_complete_task_updates_status(mock_db):
    spawn.complete_task("t-1")

    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("UPDATE sessions SET" in call for call in calls)


def test_complete_task_sets_completed(mock_db):
    spawn.complete_task("t-1")

    calls = [call[0][0] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]]
    args = [call[0][1] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]][0]
    assert TaskStatus.COMPLETED.value in args
    assert any("ended_at" in call for call in calls)


def test_fail_task_sets_failed(mock_db):
    spawn.fail_task("t-1")

    args = [call[0][1] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]][0]
    assert TaskStatus.FAILED.value in args


def test_list_tasks_returns_sessions(mock_db):
    mock_rows = [
        make_mock_row(
            {
                "id": "t-1",
                "agent_id": "a-1",
                "spawn_number": 1,
                "status": "running",
                "is_task": True,
                "constitution_hash": None,
                "channel_id": None,
                "pid": None,
                "created_at": "2024-01-01T00:00:00",
                "ended_at": None,
            }
        ),
        make_mock_row(
            {
                "id": "t-2",
                "agent_id": "a-1",
                "spawn_number": 2,
                "status": "completed",
                "is_task": True,
                "constitution_hash": None,
                "channel_id": None,
                "pid": None,
                "created_at": "2024-01-02T00:00:00",
                "ended_at": "2024-01-02T00:10:00",
            }
        ),
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_rows

    results = spawn.list_tasks()
    assert len(results) == 2
    assert results[0].id == "t-1"
    assert results[1].id == "t-2"

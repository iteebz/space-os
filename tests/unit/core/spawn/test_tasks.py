"""Spawn tasks API contract tests."""

from unittest.mock import MagicMock, patch

import pytest

from space.core import spawn
from space.core.models import TaskStatus


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


@pytest.fixture
def mock_resolve_agent():
    with patch("space.core.spawn.api.tasks.resolve_agent") as mock:
        mock.return_value = MagicMock(agent_id="agent-123")
        yield mock


def test_create_task_inserts_record(mock_db, mock_resolve_agent):
    spawn.create_task(role="test-role", input="do work")

    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    task_call = [call for call in calls if "INSERT INTO tasks" in call][0]
    assert "INSERT INTO tasks" in task_call


def test_create_task_with_channel_id(mock_db, mock_resolve_agent):
    spawn.create_task(role="test-role", input="work", channel_id="ch-123")

    calls = [
        call[0] for call in mock_db.execute.call_args_list if "INSERT INTO tasks" in call[0][0]
    ]
    assert calls
    args = calls[0][1]
    assert args[2] == "ch-123"


def test_create_task_returns_id(mock_db, mock_resolve_agent):
    result = spawn.create_task(role="test-role", input="work")
    assert result is not None


def test_create_task_unknown_role_raises(mock_resolve_agent):
    mock_resolve_agent.return_value = None

    with pytest.raises(ValueError, match="not found"):
        spawn.create_task(role="unknown", input="work")


def test_get_task_returns_task(mock_db):
    mock_row = make_mock_row(
        {
            "task_id": "t-1",
            "agent_id": "a-1",
            "channel_id": None,
            "input": "test",
            "output": None,
            "stderr": None,
            "status": "pending",
            "created_at": "2024-01-01T00:00:00",
            "started_at": None,
            "completed_at": None,
            "pid": None,
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row

    result = spawn.get_task("t-1")
    assert result is not None


def test_get_task_missing_returns_none(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None

    result = spawn.get_task("missing")
    assert result is None


def test_start_task_updates_status(mock_db):
    spawn.start_task("t-1")

    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("UPDATE tasks SET" in call for call in calls)


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
    assert any("UPDATE tasks SET" in call for call in calls)


def test_complete_task_sets_completed(mock_db):
    spawn.complete_task("t-1")

    args = [call[0][1] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]][0]
    assert TaskStatus.COMPLETED.value in args


def test_complete_task_with_output(mock_db):
    spawn.complete_task("t-1", output="success")

    args = [call[0][1] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]][0]
    assert "success" in args


def test_complete_task_with_stderr(mock_db):
    spawn.complete_task("t-1", stderr="error msg")

    args = [call[0][1] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]][0]
    assert "error msg" in args


def test_fail_task_sets_failed(mock_db):
    spawn.fail_task("t-1")

    args = [call[0][1] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]][0]
    assert TaskStatus.FAILED.value in args


def test_fail_task_with_stderr(mock_db):
    spawn.fail_task("t-1", stderr="test failed")

    args = [call[0][1] for call in mock_db.execute.call_args_list if "UPDATE" in call[0][0]][0]
    assert "test failed" in args

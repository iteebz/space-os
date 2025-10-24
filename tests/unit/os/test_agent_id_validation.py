import pytest

from space.os import events
from space.os.core.spawn import db as spawn_db


def test_emit_valid_agent_id(tmp_path, monkeypatch):
    """Valid non-empty string agent_id should be accepted"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    events.emit("test_source", "test_event", agent_id="valid-id-123")


def test_emit_none_agent_id(tmp_path, monkeypatch):
    """None agent_id should be accepted (optional param)"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    events.emit("test_source", "test_event", agent_id=None)


def test_emit_no_agent_id(tmp_path, monkeypatch):
    """Omitting agent_id should work fine"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    events.emit("test_source", "test_event", data="some data")


def test_emit_rejects_empty_agent_id(tmp_path, monkeypatch):
    """Empty string agent_id should be rejected"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    with pytest.raises(ValueError, match="agent_id must be non-empty string"):
        events.emit("test_source", "test_event", agent_id="")


def test_emit_rejects_whitespace_agent_id(tmp_path, monkeypatch):
    """Whitespace-only agent_id should be rejected"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    with pytest.raises(ValueError, match="agent_id must be non-empty string"):
        events.emit("test_source", "test_event", agent_id="   ")


def test_emit_rejects_non_string_agent_id(tmp_path, monkeypatch):
    """Non-string agent_id should be rejected"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    with pytest.raises(ValueError, match="agent_id must be str or None"):
        events.emit("test_source", "test_event", agent_id=123)  # type: ignore


def test_emit_rejects_list_agent_id(tmp_path, monkeypatch):
    """List agent_id should be rejected"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    with pytest.raises(ValueError, match="agent_id must be str or None"):
        events.emit("test_source", "test_event", agent_id=["id"])  # type: ignore


def test_logs_rejects_null_agent_id(tmp_path, monkeypatch):
    """logs() should reject tasks with null agent_id"""
    import typer

    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    from space.os.core.spawn import tasks

    spawn_db.ensure_agent("test_agent")

    task_id = spawn_db.create_task("test_agent", "test input")
    task = spawn_db.get_task(task_id)

    assert task is not None
    assert task.agent_id is not None

    with pytest.raises(typer.Exit) as exc:
        mock_task = type(task)(
            task_id=task.task_id,
            agent_id=None,
            channel_id=None,
            input=task.input,
            output=None,
            stderr=None,
            status="pending",
            pid=None,
            started_at=None,
            completed_at=None,
            created_at=task.created_at,
            duration=None,
        )
        from unittest.mock import patch

        with patch("space.os.core.spawn.db.get_task", return_value=mock_task):
            tasks.logs(task_id)

    assert exc.value.exit_code == 1


def test_ensure_agent_creates(tmp_path, monkeypatch):
    """ensure_agent should create and return valid agent_id"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    agent_id = spawn_db.ensure_agent("new_agent")

    assert agent_id is not None
    assert isinstance(agent_id, str)
    assert len(agent_id) > 0
    assert agent_id.strip() == agent_id


def test_ensure_agent_returns_existing(tmp_path, monkeypatch):
    """ensure_agent should return existing agent_id"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    agent_id_1 = spawn_db.ensure_agent("existing_agent")
    agent_id_2 = spawn_db.ensure_agent("existing_agent")

    assert agent_id_1 == agent_id_2
    assert agent_id_1 is not None
    assert isinstance(agent_id_1, str)


def test_ensure_agent_restores_archived(tmp_path, monkeypatch):
    """ensure_agent should restore archived agents"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    agent_id_1 = spawn_db.ensure_agent("archived_test")
    spawn_db.archive_agent("archived_test")

    agent_id_2 = spawn_db.ensure_agent("archived_test")

    assert agent_id_1 == agent_id_2
    assert agent_id_2 is not None
    assert isinstance(agent_id_2, str)


def test_create_task_valid_agent(tmp_path, monkeypatch):
    """create_task should succeed with valid agent"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    agent_id = spawn_db.ensure_agent("valid_agent")
    task_id = spawn_db.create_task("valid_agent", "test input")

    assert task_id is not None
    task = spawn_db.get_task(task_id)
    assert task is not None
    assert task.agent_id == agent_id


def test_create_task_rejects_nonexistent_agent(tmp_path, monkeypatch):
    """create_task should reject nonexistent agent"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    with pytest.raises(ValueError, match="Agent .* not found"):
        spawn_db.create_task("nonexistent_agent", "test input")


def test_get_agent_name_valid(tmp_path, monkeypatch):
    """get_agent_name should return name for valid agent"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    agent_id = spawn_db.ensure_agent("named_agent")
    name = spawn_db.get_agent_name(agent_id)

    assert name == "named_agent"


def test_get_agent_name_none_invalid(tmp_path, monkeypatch):
    """get_agent_name should return None for invalid agent"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    result = spawn_db.get_agent_name("nonexistent-agent-id")

    assert result is None


def test_get_agent_name_fallback(tmp_path, monkeypatch):
    """Callers should use fallback: get_agent_name(id) or 'unknown'"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    name = spawn_db.get_agent_name("bad-id") or "unknown"

    assert name == "unknown"

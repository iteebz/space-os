"""Integration test: verify agent_id data flow through critical paths."""

import pytest

from space.os import events
from space.os.core.spawn import db as spawn_db


def test_full_spawn_task_events_flow(tmp_path, monkeypatch):
    """Full path: ensure_agent → create_task → emit events"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))

    agent_id = spawn_db.ensure_agent("test_agent")
    assert agent_id is not None
    assert isinstance(agent_id, str)
    assert len(agent_id) > 0

    task_id = spawn_db.create_task("test_agent", "test input")
    assert task_id is not None

    task = spawn_db.get_task(task_id)
    assert task is not None
    assert task.agent_id == agent_id

    assert task.agent_id is not None
    assert isinstance(task.agent_id, str)

    spawn_db.update_task(task_id, status="completed", output="test output")
    updated_task = spawn_db.get_task(task_id)
    assert updated_task.status == "completed"
    assert updated_task.agent_id == agent_id


def test_invalid_agent_id_rejected_in_emit(tmp_path, monkeypatch):
    """events.emit() must reject invalid agent_id values"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))

    with pytest.raises(ValueError, match="agent_id must be non-empty string"):
        events.emit("test", "event", agent_id="")

    with pytest.raises(ValueError, match="agent_id must be str or None"):
        events.emit("test", "event", agent_id=123)  # type: ignore


def test_emit_valid_agent_id(tmp_path, monkeypatch):
    """ensure_agent output should be safe to pass to emit()"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))

    agent_id = spawn_db.ensure_agent("valid_agent")

    events.emit("spawn", "agent.test", agent_id, "test data")

    queried_events = events.query(source="spawn")
    assert len(queried_events) > 0
    assert queried_events[0].agent_id == agent_id


def test_agent_archival_preserves_invariant(tmp_path, monkeypatch):
    """Archived agents still have valid agent_id"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))

    agent_id_1 = spawn_db.ensure_agent("archivable")
    spawn_db.archive_agent("archivable")

    agent_id_2 = spawn_db.ensure_agent("archivable")

    assert agent_id_1 == agent_id_2
    assert agent_id_2 is not None
    assert isinstance(agent_id_2, str)


def test_get_agent_name_none_handling(tmp_path, monkeypatch):
    """get_agent_name(invalid_id) should return None safely"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))

    result = spawn_db.get_agent_name("nonexistent-id")
    assert result is None

    safe_result = spawn_db.get_agent_name("nonexistent-id") or "unknown"
    assert safe_result == "unknown"


def test_task_preserve_agent_id(tmp_path, monkeypatch):
    """Tasks created with channel_id should still have valid agent_id"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))

    agent_id = spawn_db.ensure_agent("channel_test")
    task_id = spawn_db.create_task("channel_test", "test input", channel_id="ch123")

    task = spawn_db.get_task(task_id)
    assert task.agent_id == agent_id
    assert task.channel_id == "ch123"
    assert task.agent_id is not None


def test_multiple_agents_distinct_ids(tmp_path, monkeypatch):
    """Multiple agents should have distinct agent_ids"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))

    id1 = spawn_db.ensure_agent("agent1")
    id2 = spawn_db.ensure_agent("agent2")
    id3 = spawn_db.ensure_agent("agent3")

    assert id1 != id2
    assert id2 != id3
    assert id1 != id3
    assert all(isinstance(id, str) for id in [id1, id2, id3])

    task1 = spawn_db.create_task("agent1", "task1")
    task2 = spawn_db.create_task("agent2", "task2")

    t1 = spawn_db.get_task(task1)
    t2 = spawn_db.get_task(task2)

    assert t1.agent_id == id1
    assert t2.agent_id == id2
    assert t1.agent_id != t2.agent_id


def test_task_list_all_have_agent_id(tmp_path, monkeypatch):
    """List tasks should all have valid agent_id"""
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))

    spawn_db.ensure_agent("lister1")
    spawn_db.ensure_agent("lister2")

    spawn_db.create_task("lister1", "task1")
    spawn_db.create_task("lister2", "task2")

    tasks = spawn_db.list_tasks()
    assert len(tasks) >= 2

    for task in tasks:
        assert task.agent_id is not None
        assert isinstance(task.agent_id, str)
        assert len(task.agent_id) > 0

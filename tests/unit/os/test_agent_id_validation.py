"""Test agent ID validation for events and spawn."""

import pytest

from space.os import events
from space.os.core.spawn import db as spawn_db


def test_emit_reject_empty_agent_id(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    with pytest.raises(ValueError, match="agent_id must be non-empty string"):
        events.emit("test_source", "test_event", agent_id="")


def test_emit_reject_whitespace_agent_id(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    with pytest.raises(ValueError, match="agent_id must be non-empty string"):
        events.emit("test_source", "test_event", agent_id="   ")


def test_emit_reject_non_string_agent_id(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    with pytest.raises(ValueError, match="agent_id must be str or None"):
        events.emit("test_source", "test_event", agent_id=123)


def test_emit_accept_valid_agent_id(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    events.emit("test_source", "test_event", agent_id="valid-id-123")


def test_emit_accept_none_agent_id(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    events.emit("test_source", "test_event", agent_id=None)


def test_ensure_agent_creates(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    agent_id = spawn_db.ensure_agent("new_agent")

    assert agent_id is not None
    assert isinstance(agent_id, str)
    assert len(agent_id) > 0


def test_ensure_agent_returns_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    id1 = spawn_db.ensure_agent("existing_agent")
    id2 = spawn_db.ensure_agent("existing_agent")

    assert id1 == id2


def test_ensure_agent_restores_archived(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    id1 = spawn_db.ensure_agent("archived_test")
    spawn_db.archive_agent("archived_test")
    id2 = spawn_db.ensure_agent("archived_test")

    assert id1 == id2


def test_create_task_requires_existing_agent(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    with pytest.raises(ValueError, match="Agent .* not found"):
        spawn_db.create_task("nonexistent_agent", "test input")


def test_get_agent_name(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    agent_id = spawn_db.ensure_agent("named_agent")
    name = spawn_db.get_agent_name(agent_id)

    assert name == "named_agent"


def test_get_agent_name_returns_none_for_invalid(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DATA", str(tmp_path))
    result = spawn_db.get_agent_name("nonexistent-agent-id")

    assert result is None

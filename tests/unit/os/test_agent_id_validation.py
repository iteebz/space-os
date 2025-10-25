"""Test agent ID validation for events and spawn."""

import pytest

from space.os import events
from space.os.core import spawn


def test_emit_reject_empty_agent_id(test_space):
    with pytest.raises(ValueError, match="agent_id must be non-empty string"):
        events.emit("test_source", "test_event", agent_id="")


def test_emit_reject_whitespace_agent_id(test_space):
    with pytest.raises(ValueError, match="agent_id must be non-empty string"):
        events.emit("test_source", "test_event", agent_id="   ")


def test_emit_reject_non_string_agent_id(test_space):
    with pytest.raises(ValueError, match="agent_id must be str or None"):
        events.emit("test_source", "test_event", agent_id=123)


def test_emit_accept_valid_agent_id(test_space):
    events.emit("test_source", "test_event", agent_id="valid-id-123")


def test_emit_accept_none_agent_id(test_space):
    events.emit("test_source", "test_event", agent_id=None)


def test_ensure_agent_creates(test_space):
    agent_id = spawn.ensure_agent("new_agent")

    assert agent_id is not None
    assert isinstance(agent_id, str)
    assert len(agent_id) > 0


def test_ensure_agent_returns_existing(test_space):
    id1 = spawn.ensure_agent("existing_agent")
    id2 = spawn.ensure_agent("existing_agent")

    assert id1 == id2


def test_ensure_agent_restores_archived(test_space):
    id1 = spawn.ensure_agent("archived_test")
    spawn.archive_agent("archived_test")
    id2 = spawn.ensure_agent("archived_test")

    assert id1 == id2


def test_create_task_requires_existing_agent(test_space):
    with pytest.raises(ValueError, match="Agent .* not found"):
        spawn.create_task("nonexistent_agent", "test input")


def test_get_agent_name(test_space):
    agent_id = spawn.ensure_agent("named_agent")
    name = spawn.get_agent_name(agent_id)

    assert name == "named_agent"


def test_get_agent_name_returns_none_for_invalid(test_space):
    result = spawn.get_agent_name("nonexistent-agent-id")

    assert result is None

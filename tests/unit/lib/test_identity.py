from space.os.spawn import db as spawn_db
from space.os.spawn import spawn


def test_inject_identity_includes_constitution(in_memory_db):
    const = "You are a test agent."
    result = spawn.inject_identity(const, "test", "test-1")

    assert "# TEST CONSTITUTION" in result
    assert "Self: You are test-1." in result
    assert "You are a test agent." in result


def test_inject_identity_with_model(in_memory_db):
    const = "You are a test agent."
    result = spawn.inject_identity(const, "test", "test-1", "claude-opus")

    assert "Self: You are test-1. Your model is claude-opus." in result


def test_self_description_persists(in_memory_db):
    spawn_db.set_self_description("agent-1", "Custom behavior")
    desc = spawn_db.get_self_description("agent-1")

    assert desc == "Custom behavior"


def test_self_description_updates(in_memory_db):
    spawn_db.set_self_description("agent-1", "First description")
    spawn_db.set_self_description("agent-1", "Updated description")
    desc = spawn_db.get_self_description("agent-1")

    assert desc == "Updated description"

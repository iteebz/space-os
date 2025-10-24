from space.os import spawn


def test_inject_includes_constitution(test_space):
    const = "You are a test agent."
    result = spawn.inject_identity(const, "test", "test-1")

    assert "# TEST CONSTITUTION" in result
    assert "Self: You are test-1." in result
    assert "You are a test agent." in result


def test_inject_with_model(test_space):
    const = "You are a test agent."
    result = spawn.inject_identity(const, "test", "test-1", "claude-opus")

    assert "Self: You are test-1. Your model is claude-opus." in result


def test_description_persist(test_space):
    spawn.db.set_self_description("agent-1", "Custom behavior")
    desc = spawn.db.get_self_description("agent-1")

    assert desc == "Custom behavior"


def test_description_update(test_space):
    spawn.db.set_self_description("agent-1", "First description")
    spawn.db.set_self_description("agent-1", "Updated description")
    desc = spawn.db.get_self_description("agent-1")

    assert desc == "Updated description"

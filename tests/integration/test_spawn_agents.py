from space.core import spawn


def test_register_agent(test_space):
    agent_id = spawn.register_agent("zealot", "zealot.md", "test-model")
    assert agent_id is not None
    agent = spawn.get_agent(agent_id)
    assert agent is not None
    assert agent.identity == "zealot"
    assert agent.constitution == "zealot.md"
    assert agent.base_agent == "test-model"


def test_register_agent_already_exists(test_space):
    spawn.register_agent("zealot", "zealot.md", "test-model")
    try:
        spawn.register_agent("zealot", "zealot.md", "test-model")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "already registered" in str(e)


def test_get_agent_by_id(test_space):
    agent_id = spawn.register_agent("zealot", "zealot.md", "test-model")
    agent = spawn.get_agent(agent_id)
    assert agent.agent_id == agent_id
    assert agent.identity == "zealot"


def test_get_agent_by_identity(test_space):
    agent_id = spawn.register_agent("zealot", "zealot.md", "test-model")
    agent = spawn.get_agent("zealot")
    assert agent.agent_id == agent_id
    assert agent.identity == "zealot"


def test_get_agent_not_found(test_space):
    agent = spawn.get_agent("nonexistent-agent")
    assert agent is None


def test_describe_self(test_space):
    agent_id = spawn.register_agent("zealot", "zealot.md", "test-model")
    spawn.describe_self("zealot", "Custom behavior")
    agent = spawn.get_agent(agent_id)
    assert agent.description == "Custom behavior"


def test_description_update(test_space):
    agent_id = spawn.register_agent("zealot", "zealot.md", "test-model")
    spawn.describe_self("zealot", "First description")
    spawn.describe_self("zealot", "Updated description")
    agent = spawn.get_agent(agent_id)
    assert agent.description == "Updated description"

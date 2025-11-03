from space.os import spawn


def test_register_agent(test_space):
    agent_id = spawn.register_agent("zealot", "claude-haiku-4-5", "zealot.md")
    assert agent_id is not None
    agent = spawn.get_agent(agent_id)
    assert agent is not None
    assert agent.identity == "zealot"
    assert agent.constitution == "zealot.md"
    assert agent.model == "claude-haiku-4-5"


def test_register_agent_already_exists(test_space):
    spawn.register_agent("zealot", "claude-haiku-4-5", "zealot.md")
    try:
        spawn.register_agent("zealot", "claude-haiku-4-5", "zealot.md")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "already registered" in str(e)


def test_get_agent_by_id(test_space):
    agent_id = spawn.register_agent("zealot", "claude-haiku-4-5", "zealot.md")
    agent = spawn.get_agent(agent_id)
    assert agent.agent_id == agent_id
    assert agent.identity == "zealot"


def test_get_agent_by_identity(test_space):
    agent_id = spawn.register_agent("zealot", "claude-haiku-4-5", "zealot.md")
    agent = spawn.get_agent("zealot")
    assert agent.agent_id == agent_id
    assert agent.identity == "zealot"


def test_get_agent_not_found(test_space):
    agent = spawn.get_agent("nonexistent-agent")
    assert agent is None

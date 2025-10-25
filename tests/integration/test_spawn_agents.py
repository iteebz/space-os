from space.core import spawn


def test_ensure_agent(test_space):
    agent_id = spawn.ensure_agent("zealot")
    assert agent_id is not None
    agent = spawn.resolve_agent(agent_id)
    assert agent is not None


def test_resolve_agent(test_space):
    agent_id = spawn.ensure_agent("zealot")
    agent = spawn.resolve_agent(agent_id)
    assert agent.agent_id == agent_id


def test_describe_self(test_space):
    agent_id = spawn.ensure_agent("zealot")
    spawn.describe_self(agent_id, "Custom behavior")
    agent = spawn.resolve_agent(agent_id)
    assert agent.description == "Custom behavior"


def test_description_update(test_space):
    agent_id = spawn.ensure_agent("zealot")
    spawn.describe_self(agent_id, "First description")
    spawn.describe_self(agent_id, "Updated description")
    agent = spawn.resolve_agent(agent_id)
    assert agent.description == "Updated description"

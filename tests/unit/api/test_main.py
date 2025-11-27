"""API endpoint tests."""

from space.api.main import get_spawn_tree
from space.os.spawn.api import agents, spawns


def test_get_spawn_tree(test_space):
    """Contract: get_spawn_tree returns spawn with recursive descendants."""
    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    root = spawns.create_spawn(agent.agent_id)
    child1 = spawns.create_spawn(agent.agent_id, parent_spawn_id=root.id)
    child2 = spawns.create_spawn(agent.agent_id, parent_spawn_id=child1.id)

    result = get_spawn_tree(root.id)

    assert result["spawn_id"] == root.id
    assert result["agent_id"] == agent.agent_id
    assert len(result["descendants"]) == 3

    descendant_ids = {d["id"] for d in result["descendants"]}
    assert descendant_ids == {root.id, child1.id, child2.id}

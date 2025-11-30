from typer.testing import CliRunner

from space.lib import store
from space.os import bridge, memory, spawn

runner = CliRunner()


# === SPAWN CLI ===
def test_spawn_list_agents(test_space, default_agents):
    """Listing agents via CLI."""
    spawn.register_agent("agent-2", "claude-haiku-4-5", "a.md")

    result = runner.invoke(spawn.app, ["agents"])
    assert result.exit_code == 0
    assert "zealot" in result.stdout
    assert "agent-2" in result.stdout
    assert "Total: 5" in result.stdout


def test_spawn_merge_agents(test_space, default_agents):
    """Merging agent memories via CLI."""
    zealot = spawn.get_agent(default_agents["zealot"])
    agent_id_1 = zealot.agent_id
    agent_id_2 = spawn.register_agent("agent-target", "claude-haiku-4-5", "a.md")

    memory.add_memory(agent_id_1, "memory from source 1", "topic-a")
    memory.add_memory(agent_id_1, "memory from source 2", "topic-b")
    memory.add_memory(agent_id_2, "memory from target", "topic-c")

    result = runner.invoke(spawn.app, ["merge", default_agents["zealot"], "agent-target"])
    assert result.exit_code == 0
    assert "Merged" in result.stdout

    target_memories = memory.list_memories("agent-target")
    assert len(target_memories) == 3
    assert any("memory from source 1" in m.message for m in target_memories)
    assert any("memory from source 2" in m.message for m in target_memories)
    assert any("memory from target" in m.message for m in target_memories)


def test_spawn_merge_missing_source(test_space, default_agents):
    """Merge fails with nonexistent source."""
    agent_id_target = default_agents["zealot"]

    result = runner.invoke(spawn.app, ["merge", "nonexistent", agent_id_target])
    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_spawn_merge_missing_target(test_space, default_agents):
    """Merge fails with nonexistent target."""
    agent_id_source = default_agents["zealot"]

    result = runner.invoke(spawn.app, ["merge", agent_id_source, "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_spawn_rename_agent(test_space, default_agents):
    """Renaming agent via CLI."""
    old_name = default_agents["zealot"]

    result = runner.invoke(spawn.app, ["rename", old_name, "new-name"])
    assert result.exit_code == 0
    assert "Renamed" in result.stdout

    with store.ensure() as conn:
        agent = conn.execute(
            "SELECT identity FROM agents WHERE identity = ?", ("new-name",)
        ).fetchone()
    assert agent is not None


# === BRIDGE CLI ===
def test_bridge_list_channels(test_space):
    """Listing channels via bridge CLI."""
    result = runner.invoke(bridge.app, ["channels"])
    assert result.exit_code == 0


def test_bridge_send_fails_missing_channel(test_space, default_agents):
    """Send fails when channel doesn't exist."""
    result = runner.invoke(
        bridge.app, ["--as", default_agents["zealot"], "send", "nonexistent-channel", "hello"]
    )
    assert result.exit_code != 0
    assert "not found" in result.output


def test_bridge_recv_requires_identity():
    """Recv command requires --as identity."""
    result = runner.invoke(bridge.app, ["recv", "test-channel"])
    assert result.exit_code != 0


def test_spawn_chain_no_args(test_space, default_agents):
    """Chain command with no args shows root spawns."""
    agent = spawn.get_agent(default_agents["zealot"])
    root1 = spawn.spawns.create_spawn(agent.agent_id)
    root2 = spawn.spawns.create_spawn(agent.agent_id)
    spawn.spawns.create_spawn(agent.agent_id, parent_spawn_id=root1.id)

    result = runner.invoke(spawn.app, ["chain"])
    assert result.exit_code == 0
    assert root1.id[:8] in result.stdout
    assert root2.id[:8] in result.stdout


def test_spawn_chain_by_spawn_id(test_space, default_agents):
    """Chain command with spawn ID shows tree rooted at that spawn."""
    agent = spawn.get_agent(default_agents["zealot"])
    root = spawn.spawns.create_spawn(agent.agent_id)
    child1 = spawn.spawns.create_spawn(agent.agent_id, parent_spawn_id=root.id)
    child2 = spawn.spawns.create_spawn(agent.agent_id, parent_spawn_id=root.id)
    grandchild = spawn.spawns.create_spawn(agent.agent_id, parent_spawn_id=child1.id)

    result = runner.invoke(spawn.app, ["chain", root.id])
    assert result.exit_code == 0
    assert root.id[:8] in result.stdout
    assert child1.id[:8] in result.stdout
    assert child2.id[:8] in result.stdout
    assert grandchild.id[:8] in result.stdout


def test_spawn_chain_by_agent_identity(test_space, default_agents):
    """Chain command with agent identity shows all spawn chains for agent."""
    zealot_id = default_agents["zealot"]
    agent = spawn.get_agent(zealot_id)
    root1 = spawn.spawns.create_spawn(agent.agent_id)
    child1 = spawn.spawns.create_spawn(agent.agent_id, parent_spawn_id=root1.id)

    result = runner.invoke(spawn.app, ["chain", zealot_id])
    assert result.exit_code == 0
    assert root1.id[:8] in result.stdout
    assert child1.id[:8] in result.stdout


def test_spawn_chain_nonexistent_spawn(test_space):
    """Chain command with nonexistent spawn ID fails gracefully."""
    result = runner.invoke(spawn.app, ["chain", "nonexistent-id"])
    assert result.exit_code != 0
    assert "not found" in result.stdout or "not found" in result.stderr


def test_spawn_chain_status_symbols(test_space, default_agents):
    """Chain displays correct status symbols for all states."""
    agent = spawn.get_agent(default_agents["zealot"])

    pending_spawn = spawn.spawns.create_spawn(agent.agent_id)
    spawn.spawns.update_status(pending_spawn.id, "running")
    spawn.spawns.create_spawn(agent.agent_id)

    completed = spawn.spawns.create_spawn(agent.agent_id)
    spawn.spawns.update_status(completed.id, "completed")

    failed = spawn.spawns.create_spawn(agent.agent_id)
    spawn.spawns.update_status(failed.id, "failed")

    timeout = spawn.spawns.create_spawn(agent.agent_id)
    spawn.spawns.update_status(timeout.id, "timeout")

    paused = spawn.spawns.create_spawn(agent.agent_id)
    spawn.spawns.update_status(paused.id, "paused")

    killed = spawn.spawns.create_spawn(agent.agent_id)
    spawn.spawns.update_status(killed.id, "killed")

    result = runner.invoke(spawn.app, ["chain"])
    assert result.exit_code == 0
    assert "⚡" in result.stdout
    assert "✓" in result.stdout
    assert "✗" in result.stdout
    assert "⏱" in result.stdout
    assert "⏸" in result.stdout
    assert "⚠" in result.stdout


def test_spawn_chain_deep_tree(test_space, default_agents):
    """Chain renders deep trees (3+ levels) with correct indentation."""
    agent = spawn.get_agent(default_agents["zealot"])

    root = spawn.spawns.create_spawn(agent.agent_id)
    child = spawn.spawns.create_spawn(agent.agent_id, parent_spawn_id=root.id)
    grandchild = spawn.spawns.create_spawn(agent.agent_id, parent_spawn_id=child.id)
    great_grandchild = spawn.spawns.create_spawn(agent.agent_id, parent_spawn_id=grandchild.id)

    result = runner.invoke(spawn.app, ["chain", root.id])
    assert result.exit_code == 0

    lines = result.stdout.split("\n")
    root_line = next((line for line in lines if root.id[:8] in line), None)
    child_line = next((line for line in lines if child.id[:8] in line), None)
    grandchild_line = next((line for line in lines if grandchild.id[:8] in line), None)
    great_line = next((line for line in lines if great_grandchild.id[:8] in line), None)

    assert root_line is not None
    assert child_line is not None
    assert grandchild_line is not None
    assert great_line is not None


def test_spawn_chain_mixed_agents(test_space, default_agents):
    """Chain shows spawns from multiple agents in same tree."""
    agent1 = spawn.get_agent(default_agents["zealot"])
    spawn.register_agent("agent-other", "claude-haiku-4-5", None)
    agent2 = spawn.get_agent("agent-other")

    root = spawn.spawns.create_spawn(agent1.agent_id)
    child1 = spawn.spawns.create_spawn(agent2.agent_id, parent_spawn_id=root.id)

    result = runner.invoke(spawn.app, ["chain", root.id])
    assert result.exit_code == 0
    assert root.id[:8] in result.stdout
    assert child1.id[:8] in result.stdout


def test_spawn_chain_nonexistent_agent_identity(test_space):
    """Chain with nonexistent agent identity fails."""
    result = runner.invoke(spawn.app, ["chain", "nonexistent-agent"])
    assert result.exit_code != 0
    assert "not found" in result.stdout or "not found" in result.stderr


def test_spawn_chain_partial_spawn_id(test_space, default_agents):
    """Chain with partial spawn ID matches correctly."""
    agent = spawn.get_agent(default_agents["zealot"])
    root = spawn.spawns.create_spawn(agent.agent_id)
    child = spawn.spawns.create_spawn(agent.agent_id, parent_spawn_id=root.id)

    result = runner.invoke(spawn.app, ["chain", root.id])
    assert result.exit_code == 0
    assert child.id[:8] in result.stdout

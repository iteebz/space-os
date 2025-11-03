from typer.testing import CliRunner

from space.core import db
from space.os import bridge, memory, spawn

runner = CliRunner()


# === SPAWN CLI ===
def test_spawn_list_agents(test_space, default_agents):
    """Listing agents via CLI."""
    zealot_id = default_agents["zealot"]
    spawn.register_agent("agent-2", "claude-haiku-4-5", "a.md")

    result = runner.invoke(spawn.app, ["agents"])
    assert result.exit_code == 0
    assert zealot_id in result.stdout
    assert "agent-2" in result.stdout


def test_spawn_merge_agents(test_space, default_agents):
    """Merging agent memories via CLI."""
    zealot = spawn.get_agent(default_agents["zealot"])
    agent_id_1 = zealot.agent_id
    agent_id_2 = spawn.register_agent("agent-target", "claude-haiku-4-5", "a.md")

    memory.api.add_memory(agent_id_1, "memory from source 1", "topic-a")
    memory.api.add_memory(agent_id_1, "memory from source 2", "topic-b")
    memory.api.add_memory(agent_id_2, "memory from target", "topic-c")

    result = runner.invoke(spawn.app, ["merge", default_agents["zealot"], "agent-target"])
    assert result.exit_code == 0
    assert "Merged" in result.stdout

    target_memories = memory.api.list_memories("agent-target")
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

    with db.connect() as conn:
        agent = conn.execute(
            "SELECT identity FROM agents WHERE identity = ?", ("new-name",)
        ).fetchone()
    assert agent is not None


# === BRIDGE CLI ===
def test_bridge_list_channels(test_space):
    """Listing channels via bridge CLI."""
    result = runner.invoke(bridge.app, ["channels"])
    assert result.exit_code == 0


def test_bridge_channels_list(test_space):
    """Listing channels via bridge channels subcommand."""
    result = runner.invoke(bridge.app, ["channels"])
    assert result.exit_code == 0


def test_bridge_inbox_requires_identity():
    """Inbox command requires --as identity."""
    result = runner.invoke(bridge.app, ["inbox"])
    assert result.exit_code != 0


def test_bridge_send_fails_missing_channel(test_space, default_agents):
    """Send fails when channel doesn't exist."""
    result = runner.invoke(
        bridge.app, ["send", "nonexistent-channel", "hello", "--as", default_agents["zealot"]]
    )
    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_bridge_recv_requires_identity():
    """Recv command requires --as identity."""
    result = runner.invoke(bridge.app, ["recv", "test-channel"])
    assert result.exit_code != 0

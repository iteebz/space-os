"""CLI integration tests - entry points, commands, and user-facing flows."""

from typer.testing import CliRunner

from space.core import bridge, memory, spawn

runner = CliRunner()


# === SPAWN CLI ===
def test_spawn_list_agents(test_space):
    """Listing agents via CLI."""
    spawn.ensure_agent("agent-1")
    spawn.ensure_agent("agent-2")

    result = runner.invoke(spawn.app, ["agents"])
    assert result.exit_code == 0
    assert "agent-1" in result.stdout
    assert "agent-2" in result.stdout


def test_spawn_merge_agents(test_space):
    """Merging agent memories via CLI."""
    agent_id_1 = spawn.ensure_agent("agent-source")
    agent_id_2 = spawn.ensure_agent("agent-target")

    memory.add_entry(agent_id_1, "topic-a", "memory from source 1")
    memory.add_entry(agent_id_1, "topic-b", "memory from source 2")
    memory.add_entry(agent_id_2, "topic-c", "memory from target")

    result = runner.invoke(spawn.app, ["merge", "agent-source", "agent-target"])
    assert result.exit_code == 0
    assert "Merged" in result.stdout

    target_memories = memory.list_entries("agent-target")
    assert len(target_memories) == 3
    assert any("memory from source 1" in m.message for m in target_memories)
    assert any("memory from source 2" in m.message for m in target_memories)
    assert any("memory from target" in m.message for m in target_memories)


def test_spawn_merge_missing_source(test_space):
    """Merge fails with nonexistent source."""
    spawn.ensure_agent("agent-target")

    result = runner.invoke(spawn.app, ["merge", "nonexistent", "agent-target"])
    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_spawn_merge_missing_target(test_space):
    """Merge fails with nonexistent target."""
    spawn.ensure_agent("agent-source")

    result = runner.invoke(spawn.app, ["merge", "agent-source", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_spawn_rename_agent(test_space):
    """Renaming agent via CLI."""
    spawn.ensure_agent("old-name")

    result = runner.invoke(spawn.app, ["rename", "old-name", "new-name"])
    assert result.exit_code == 0
    assert "Renamed" in result.stdout

    with spawn.db.connect() as conn:
        agent = conn.execute(
            "SELECT identity FROM agents WHERE identity = ?", ("new-name",)
        ).fetchone()
    assert agent is not None


# === BRIDGE CLI ===
def test_bridge_shows_readme():
    """Running bridge without args shows README."""
    result = runner.invoke(bridge.app)
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_bridge_list_channels(test_space):
    """Listing channels via bridge CLI."""
    result = runner.invoke(bridge.app, ["list"])
    assert result.exit_code == 0


def test_bridge_channels_list(test_space):
    """Listing channels via bridge channels subcommand."""
    result = runner.invoke(bridge.app, ["channels", "list"])
    assert result.exit_code == 0


def test_bridge_inbox_requires_identity():
    """Inbox command requires --as identity."""
    result = runner.invoke(bridge.app, ["inbox"])
    assert result.exit_code != 0


def test_bridge_inbox_with_identity(test_space):
    """Inbox command with identity."""
    result = runner.invoke(bridge.app, ["inbox", "--as", "test-agent"])
    assert result.exit_code == 0


def test_bridge_send_creates_channel(test_space):
    """Send creates missing channel automatically."""
    result = runner.invoke(bridge.app, ["send", "test-channel", "hello", "--as", "test-agent"])
    assert result.exit_code == 0


def test_bridge_recv_requires_identity():
    """Recv command requires --as identity."""
    result = runner.invoke(bridge.app, ["recv", "test-channel"])
    assert result.exit_code != 0


def test_bridge_export_channel(test_space):
    """Export channel returns markdown format."""
    runner.invoke(bridge.app, ["send", "export-test", "hello world", "--as", "alice"])

    result = runner.invoke(bridge.app, ["export", "export-test"])
    assert result.exit_code == 0
    assert "export-test" in result.stdout
    assert "hello world" in result.stdout

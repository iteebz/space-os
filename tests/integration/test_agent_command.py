from typer.testing import CliRunner

from space.commands.agent import app
from space.memory import db
from space.spawn import registry

runner = CliRunner()


def test_agent_list(test_space):
    """Test listing agents."""
    registry.init_db()
    registry.ensure_agent("agent-1")
    registry.ensure_agent("agent-2")

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "agent-1" in result.stdout
    assert "agent-2" in result.stdout


def test_agent_merge(test_space):
    """Test merging agent memories from one ID to another."""
    registry.init_db()
    agent_id_1 = registry.ensure_agent("agent-source")
    agent_id_2 = registry.ensure_agent("agent-target")

    db.add_entry(agent_id_1, "topic-a", "memory from source 1")
    db.add_entry(agent_id_1, "topic-b", "memory from source 2")
    db.add_entry(agent_id_2, "topic-c", "memory from target")

    result = runner.invoke(app, ["merge", "agent-source", "agent-target"])
    assert result.exit_code == 0
    assert "Merged" in result.stdout

    target_memories = db.get_memories("agent-target")

    assert len(target_memories) == 3
    assert any("memory from source 1" in m.message for m in target_memories)
    assert any("memory from source 2" in m.message for m in target_memories)
    assert any("memory from target" in m.message for m in target_memories)


def test_agent_merge_nonexistent_source(test_space):
    """Test merge fails with nonexistent source agent."""
    registry.init_db()
    registry.ensure_agent("agent-target")

    result = runner.invoke(app, ["merge", "nonexistent", "agent-target"])
    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_agent_merge_nonexistent_target(test_space):
    """Test merge fails with nonexistent target agent."""
    registry.init_db()
    registry.ensure_agent("agent-source")

    result = runner.invoke(app, ["merge", "agent-source", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_agent_rename(test_space):
    """Test renaming an agent."""
    registry.init_db()
    registry.ensure_agent("old-name")

    result = runner.invoke(app, ["rename", "old-name", "new-name"])
    assert result.exit_code == 0
    assert "Renamed" in result.stdout

    with registry.get_db() as conn:
        agent = conn.execute("SELECT name FROM agents WHERE name = ?", ("new-name",)).fetchone()
    assert agent is not None

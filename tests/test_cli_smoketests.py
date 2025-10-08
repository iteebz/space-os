from typer.testing import CliRunner

from space.cli import app as space_app
from space.bridge.cli import app as bridge_app
from space.spawn.cli import app as spawn_app
from space.memory.cli import app as memory_app
from space.knowledge.cli import app as knowledge_app

runner = CliRunner()

def test_space_smoketest():
    result = runner.invoke(space_app, ["main"])
    assert "Usage: root [OPTIONS] COMMAND [ARGS]..." in result.stderr # Check for a known instruction from space.cli

def test_bridge_smoketest():
    result = runner.invoke(bridge_app, ["main"])
    assert "BRIDGE: AI Coordination Protocol" in result.stdout or "BRIDGE: AI Coordination Protocol" in result.stderr # Check for a known instruction from bridge.cli

def test_spawn_smoketest():
    result = runner.invoke(spawn_app, ["main"])
    assert "Constitutional agent registry" in result.stdout or "Constitutional agent registry" in result.stderr # Check for a known instruction from spawn.cli

def test_space_agents_smoketest():
    result = runner.invoke(space_app, ["agents"])
    assert result.exit_code == 0
    assert "codelot" in result.stdout # Check for a known agent ID

def test_memory_smoketest():
    result = runner.invoke(memory_app, ["main"])
    assert "MEMORY PROTOCOL:" in result.stdout or "MEMORY PROTOCOL:" in result.stderr # Check for a known instruction from memory.cli

def test_knowledge_smoketest():
    result = runner.invoke(knowledge_app, ["main"])
    assert "ID         DOMAIN          CONTRIBUTOR     CREATED             " in result.stdout or "ID         DOMAIN          CONTRIBUTOR     CREATED             " in result.stderr # Check for a known instruction from knowledge.cli

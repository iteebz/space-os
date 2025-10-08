from typer.testing import CliRunner

from space.bridge.cli import app as bridge_app
from space.cli import app as space_app
from space.knowledge.cli import app as knowledge_app
from space.memory.cli import app as memory_app
from space.spawn.cli import app as spawn_app

runner = CliRunner()


def test_space_smoketest():
    result = runner.invoke(space_app)
    assert "WELCOME TO AGENT-SPACE" in result.stdout


def test_bridge_smoketest():
    result = runner.invoke(bridge_app)

    assert (
        "IDENTITY SYSTEM:" in result.stdout or "IDENTITY SYSTEM:" in result.stderr
    )  # Check for a known instruction from bridge.cli


def test_spawn_smoketest():
    result = runner.invoke(spawn_app)

    assert (
        "Constitutional agent registry" in result.stdout
        or "Constitutional agent registry" in result.stderr
    )  # Check for a known instruction from spawn.cli


def test_space_agents_smoketest():
    result = runner.invoke(space_app, ["agents"])

    assert result.exit_code == 0

    assert "codelot" in result.stdout  # Check for a known agent ID


def test_memory_smoketest():
    result = runner.invoke(memory_app)

    assert (
        "MEMORY PROTOCOL:" in result.stdout or "MEMORY PROTOCOL:" in result.stderr
    )  # Check for a known instruction from memory.cli


def test_knowledge_smoketest():
    result = runner.invoke(knowledge_app)

    assert (
        "ID         DOMAIN          CONTRIBUTOR     CREATED             " in result.stdout
        or "ID         DOMAIN          CONTRIBUTOR     CREATED             " in result.stderr
    )  # Check for a known instruction from knowledge.cli

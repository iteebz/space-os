"""Test that all apps show their README when invoked without commands."""

from typer.testing import CliRunner

from space.bridge.app import app as bridge_app
from space.context.app import app as context_app
from space.knowledge.app import app as knowledge_app
from space.memory.app import app as memory_app

runner = CliRunner()


def test_bridge_shows_readme():
    result = runner.invoke(bridge_app)
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_memory_shows_readme():
    result = runner.invoke(memory_app)
    assert result.exit_code == 0
    assert "memory" in result.stdout.lower()


def test_knowledge_shows_readme():
    result = runner.invoke(knowledge_app)
    assert result.exit_code == 0
    assert "knowledge" in result.stdout.lower()


def test_context_shows_readme():
    result = runner.invoke(context_app)
    assert result.exit_code == 0
    assert "context" in result.stdout.lower()

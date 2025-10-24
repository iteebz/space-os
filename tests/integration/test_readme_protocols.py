"""Test README protocol: apps show docs by default (no args or --help)."""

from typer.testing import CliRunner

from space.cli import app as space_app
from space.os.bridge.app import app as bridge_app
from space.os.context.app import app as context_app
from space.os.knowledge.app import app as knowledge_app
from space.os.memory.app import app as memory_app

runner = CliRunner()


def test_space_no_args():
    """space shows README by default."""
    result = runner.invoke(space_app)
    assert result.exit_code == 0
    assert "Welcome to space-os" in result.stdout


def test_space_help():
    """space --help shows README."""
    result = runner.invoke(space_app, ["--help"])
    assert result.exit_code == 0
    assert "space" in result.stdout.lower()


def test_bridge_no_args():
    """bridge shows README by default."""
    result = runner.invoke(bridge_app)
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_bridge_help():
    """bridge --help shows README."""
    result = runner.invoke(bridge_app, ["--help"])
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_memory_no_args():
    """memory shows README by default."""
    result = runner.invoke(memory_app)
    assert result.exit_code == 0
    assert "memory" in result.stdout.lower()


def test_memory_help():
    """memory --help shows README."""
    result = runner.invoke(memory_app, ["--help"])
    assert result.exit_code == 0
    assert result.stdout


def test_knowledge_no_args():
    """knowledge shows README by default."""
    result = runner.invoke(knowledge_app)
    assert result.exit_code == 0
    assert "knowledge" in result.stdout.lower()


def test_knowledge_help():
    """knowledge --help shows README."""
    result = runner.invoke(knowledge_app, ["--help"])
    assert result.exit_code == 0
    assert result.stdout


def test_context_no_args():
    """context shows README by default."""
    result = runner.invoke(context_app)
    assert result.exit_code == 0
    assert "context" in result.stdout.lower()


def test_context_help():
    """context --help shows README."""
    result = runner.invoke(context_app, ["--help"])
    assert result.exit_code == 0
    assert result.stdout

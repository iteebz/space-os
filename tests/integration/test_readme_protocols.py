"""Test README protocol: apps show docs by default (no args or --help)."""

from typer.testing import CliRunner

from space.apps.context.app import app as context_app
from space.cli import app as space_app
from space.os import bridge, knowledge, memory

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
    result = runner.invoke(bridge)
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_bridge_help():
    """bridge --help shows README."""
    result = runner.invoke(bridge, ["--help"])
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_memory_no_args():
    """memory shows README by default."""
    result = runner.invoke(memory)
    assert result.exit_code == 0
    assert "memory" in result.stdout.lower()


def test_memory_help():
    """memory --help shows README."""
    result = runner.invoke(memory, ["--help"])
    assert result.exit_code == 0
    assert result.stdout


def test_knowledge_no_args():
    """knowledge shows README by default."""
    result = runner.invoke(knowledge)
    assert result.exit_code == 0
    assert "knowledge" in result.stdout.lower()


def test_knowledge_help():
    """knowledge --help shows README."""
    result = runner.invoke(knowledge, ["--help"])
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

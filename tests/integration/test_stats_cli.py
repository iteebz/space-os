"""Test stats CLI commands."""

from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_overview_command(test_space):
    """Overview command outputs successfully."""
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "overview" in result.stdout


def test_memory_command_not_initialized(test_space):
    """Memory command handles uninitialized state."""
    result = runner.invoke(app, ["stats", "memory"])
    assert result.exit_code == 0
    assert "memory not initialized" in result.stdout or "no entries yet" in result.stdout


def test_knowledge_command_not_initialized(test_space):
    """Knowledge command handles uninitialized state."""
    result = runner.invoke(app, ["stats", "knowledge"])
    assert result.exit_code == 0
    assert "knowledge not initialized" in result.stdout or "no entries yet" in result.stdout


def test_bridge_command_not_initialized(test_space):
    """Bridge command handles uninitialized state."""
    result = runner.invoke(app, ["stats", "bridge"])
    assert result.exit_code == 0
    assert "bridge not initialized" in result.stdout or "no messages yet" in result.stdout

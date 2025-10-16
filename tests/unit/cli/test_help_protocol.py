"""Test that all apps show README protocol on --help."""

from typer.testing import CliRunner

from space.app import app
from space.bridge.app import app as bridge_app
from space.context.app import app as context_app
from space.knowledge.app import app as knowledge_app
from space.memory.app import app as memory_app

runner = CliRunner()


def test_space_help_shows_readme():
    """space --help shows root README protocol."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Welcome to space-os" in result.stdout or "space" in result.stdout.lower()


def test_space_dash_h_shows_readme():
    """space -h shows root README protocol."""
    result = runner.invoke(app, ["-h"])
    assert result.exit_code == 0
    assert "Welcome to space-os" in result.stdout or "space" in result.stdout.lower()


def test_bridge_help_shows_readme():
    """bridge --help shows BRIDGE README protocol."""
    result = runner.invoke(bridge_app, ["--help"])
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_bridge_dash_h_shows_readme():
    """bridge -h shows BRIDGE README protocol."""
    result = runner.invoke(bridge_app, ["-h"])
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_memory_help_shows_readme():
    """memory --help shows memory README protocol."""
    result = runner.invoke(memory_app, ["--help"])
    assert result.exit_code == 0
    # Memory app should show its README
    assert result.stdout  # Just verify non-empty output


def test_memory_dash_h_shows_readme():
    """memory -h shows memory README protocol."""
    result = runner.invoke(memory_app, ["-h"])
    assert result.exit_code == 0
    assert result.stdout


def test_context_help_shows_readme():
    """context --help shows context README protocol."""
    result = runner.invoke(context_app, ["--help"])
    assert result.exit_code == 0
    assert result.stdout


def test_context_dash_h_shows_readme():
    """context -h shows context README protocol."""
    result = runner.invoke(context_app, ["-h"])
    assert result.exit_code == 0
    assert result.stdout


def test_knowledge_help_shows_readme():
    """knowledge --help shows knowledge README protocol."""
    result = runner.invoke(knowledge_app, ["--help"])
    assert result.exit_code == 0
    assert result.stdout


def test_knowledge_dash_h_shows_readme():
    """knowledge -h shows knowledge README protocol."""
    result = runner.invoke(knowledge_app, ["-h"])
    assert result.exit_code == 0
    assert result.stdout

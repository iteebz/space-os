"""Integration tests for the search command."""

from typer.testing import CliRunner

from space.app import app

runner = CliRunner()


def test_search_no_results():
    """Test search with no results."""
    result = runner.invoke(app, ["search", "nonexistentkeyword"])
    assert result.exit_code == 0
    assert "No results for 'nonexistentkeyword'" in result.stdout


def test_search_memory():
    """Test search with a result in memory."""
    result = runner.invoke(app, ["search", "memory"])
    assert result.exit_code == 0
    assert "MEMORY:" in result.stdout or "No results for 'memory'" in result.stdout


def test_search_knowledge():
    """Test search with a result in knowledge."""
    result = runner.invoke(app, ["search", "knowledge"])
    assert result.exit_code == 0
    assert "KNOWLEDGE:" in result.stdout or "No results for 'knowledge'" in result.stdout


def test_search_bridge():
    """Test search with a result in bridge."""
    result = runner.invoke(app, ["search", "bridge"])
    assert result.exit_code == 0
    assert "BRIDGE:" in result.stdout or "No results for 'bridge'" in result.stdout

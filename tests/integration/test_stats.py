from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_stats_shows_overview():
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "overview" in result.stdout
    assert "___" in result.stdout


def test_stats_memory():
    result = runner.invoke(app, ["stats", "memory"])
    assert result.exit_code == 0
    assert "memory" in result.stdout


def test_stats_knowledge():
    result = runner.invoke(app, ["stats", "knowledge"])
    assert result.exit_code == 0
    assert "knowledge" in result.stdout


def test_stats_bridge():
    result = runner.invoke(app, ["stats", "bridge"])
    assert result.exit_code == 0
    assert "bridge" in result.stdout

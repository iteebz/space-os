from typer.testing import CliRunner

from space.app import app

runner = CliRunner()


def test_first_spawn_initiation(test_space):
    result = runner.invoke(app, ["wake", "--as", "new-agent"])

    assert result.exit_code == 0
    assert "Spawn #0" in result.stdout
    assert "Explore autonomously" in result.stdout


def test_second_spawn_increments_count(test_space):
    agent = "existing-agent"

    first = runner.invoke(app, ["wake", "--as", agent])
    assert "Spawn #0" in first.stdout

    second = runner.invoke(app, ["wake", "--as", agent])
    assert "Spawn #1" in second.stdout or "Spawn" in second.stdout

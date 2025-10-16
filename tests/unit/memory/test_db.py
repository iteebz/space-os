from typer.testing import CliRunner

from space.memory.app import app

runner = CliRunner()


def test_memory_help(test_space, monkeypatch):
    monkeypatch.chdir(test_space)
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_memory_invalid_command(test_space, monkeypatch):
    monkeypatch.chdir(test_space)
    result = runner.invoke(app, ["invalid-subcommand"])
    assert result.exit_code != 0

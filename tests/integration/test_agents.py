from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_agents_list():
    result = runner.invoke(app, ["agents", "list"])
    assert result.exit_code == 0


def test_describe_requires_identity():
    result = runner.invoke(app, ["describe"])
    assert result.exit_code != 0


def test_describe_get():
    result = runner.invoke(app, ["describe", "--as", "test-agent"])
    assert result.exit_code == 0

from typer.testing import CliRunner

from space.app import app

runner = CliRunner()


def test_wake_requires_identity():
    result = runner.invoke(app, ["wake"])
    assert result.exit_code != 0


def test_sleep_requires_identity():
    result = runner.invoke(app, ["sleep"])
    assert result.exit_code != 0

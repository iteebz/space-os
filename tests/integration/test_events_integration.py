from typer.testing import CliRunner

from space.app import app

runner = CliRunner()


def test_events_shows_output():
    result = runner.invoke(app, ["events"])
    assert result.exit_code == 0


def test_events_with_limit():
    result = runner.invoke(app, ["events", "--limit", "5"])
    assert result.exit_code == 0


def test_events_with_json():
    result = runner.invoke(app, ["events", "--json"])
    assert result.exit_code == 0

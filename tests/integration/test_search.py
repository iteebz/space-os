from typer.testing import CliRunner

from space.app import app

runner = CliRunner()


def test_search_requires_query():
    result = runner.invoke(app, ["search"])
    assert result.exit_code != 0


def test_search_with_query():
    result = runner.invoke(app, ["search", "test"])
    assert result.exit_code == 0


def test_context_requires_query():
    result = runner.invoke(app, ["context", "test"])
    assert result.exit_code == 0


def test_context_with_query():
    result = runner.invoke(app, ["context", "test"])
    assert result.exit_code == 0

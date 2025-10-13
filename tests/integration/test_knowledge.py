from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_knowledge_list():
    result = runner.invoke(app, ["knowledge", "list"])
    assert result.exit_code == 0


def test_add_requires_identity():
    result = runner.invoke(app, ["knowledge", "add", "test content"])
    assert result.exit_code != 0

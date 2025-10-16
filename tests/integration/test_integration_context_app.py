from typer.testing import CliRunner

from space.app import app

runner = CliRunner()


def test_readme_no_args():
    result = runner.invoke(app, ["context"])
    assert result.exit_code == 0
    assert "Unified search" in result.stdout

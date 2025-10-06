from click.testing import CliRunner
from space.cli import main

def test_example_smoketest():
    runner = CliRunner()
    result = runner.invoke(main, ["example", "--help"])
    assert result.exit_code == 0
    assert "Usage: main example [OPTIONS] COMMAND [ARGS]..." in result.output
    assert "Example app CLI." in result.output
    assert "Options:" in result.output
    assert "--help  Show this message and exit." in result.output
    assert "Commands:" in result.output
    assert "reverse  Reverses a given string." in result.output

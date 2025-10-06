from click.testing import CliRunner
from space.cli import main

def test_register_smoketest():
    runner = CliRunner()
    result = runner.invoke(main, ["register", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(main, ["register"])
    assert result.exit_code == 0
    assert "# Register Guide" in result.output
    assert "This guide explains how to use the register primitive." in result.output

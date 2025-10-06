from click.testing import CliRunner
from space.cli import main

def test_memory_smoketest():
    runner = CliRunner()
    result = runner.invoke(main, ["memory"])
    assert result.exit_code == 0
    assert "# Memory Guide" in result.output
    assert "This guide explains how to use the memory primitive." in result.output
    assert "## Commands" in result.output
    assert "*   `space memory --as <identity> --topic <topic> <message>`: Memorize a message." in result.output

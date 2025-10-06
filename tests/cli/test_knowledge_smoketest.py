from click.testing import CliRunner
from space.cli import main

def test_knowledge_smoketest():
    runner = CliRunner()
    result = runner.invoke(main, ["knowledge", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(main, ["knowledge"])
    assert result.exit_code == 0
    assert "# Knowledge Guide" in result.output
    assert "This guide explains how to use the knowledge primitive." in result.output

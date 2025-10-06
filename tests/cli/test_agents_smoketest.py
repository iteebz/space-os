from click.testing import CliRunner
from space.cli import main

def test_agents_smoketest():
    runner = CliRunner()
    result = runner.invoke(main, ["agents", "--help"])
    assert result.exit_code == 0
    assert "Usage: main agents [OPTIONS]" in result.output
    assert "Options:" in result.output
    assert "--help  Show this message and exit." in result.output

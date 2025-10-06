from click.testing import CliRunner
from space.cli import main

def test_spawn_smoketest():
    runner = CliRunner()
    result = runner.invoke(main, ["spawn", "--help"])
    assert result.exit_code == 0
    assert "Usage: main spawn [OPTIONS] COMMAND [ARGS]..." in result.output
    assert "Commands for spawning and managing agents." in result.output
    assert "Options:" in result.output
    assert "--help  Show this message and exit." in result.output
    assert "Commands:" in result.output
    assert "spawn  Spawns an agent and registers it with the system." in result.output

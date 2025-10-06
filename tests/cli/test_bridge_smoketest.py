from click.testing import CliRunner
from space.cli import main

def test_bridge_smoketest():
    runner = CliRunner()
    result = runner.invoke(main, ["bridge", "--help"])
    assert result.exit_code == 0
    assert "Usage: main bridge [OPTIONS] COMMAND [ARGS]..." in result.output
    assert "Options:" in result.output
    assert "--help  Show this message and exit." in result.output
    assert "Commands:" in result.output
    assert "alert         Send high-priority alert to a channel." in result.output
    assert "channels      List all channels." in result.output
    assert "send          Send a message to a channel." in result.output
    assert "stream        Stream all bridge events in real-time." in result.output

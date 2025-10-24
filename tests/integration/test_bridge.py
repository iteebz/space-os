from typer.testing import CliRunner

from space.os.core.bridge import bridge

runner = CliRunner()


def test_bridge_shows_readme():
    result = runner.invoke(bridge)
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_bridge_list_channels(test_space):
    result = runner.invoke(bridge, ["list"])
    assert result.exit_code == 0


def test_bridge_channels_list(test_space):
    result = runner.invoke(bridge, ["channels", "list"])
    assert result.exit_code == 0


def test_bridge_inbox_requires_identity():
    result = runner.invoke(bridge, ["inbox"])
    assert result.exit_code != 0


def test_bridge_inbox_with_identity(test_space):
    result = runner.invoke(bridge, ["inbox", "--as", "test-agent"])
    assert result.exit_code == 0


def test_send_creates_missing_channel(test_space):
    result = runner.invoke(bridge, ["send", "test-channel", "hello", "--as", "test-agent"])
    assert result.exit_code == 0


def test_bridge_recv_requires_identity():
    result = runner.invoke(bridge, ["recv", "test-channel"])
    assert result.exit_code != 0


def test_bridge_export_channel(test_space):
    """Export channel returns markdown format."""
    # First create a channel with a message
    runner.invoke(bridge, ["send", "export-test", "hello world", "--as", "alice"])

    # Export it
    result = runner.invoke(bridge, ["export", "export-test"])
    assert result.exit_code == 0
    assert "export-test" in result.stdout
    assert "hello world" in result.stdout

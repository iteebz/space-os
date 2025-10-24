from typer.testing import CliRunner

from space.os.bridge.app import app

runner = CliRunner()


def test_bridge_shows_readme():
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "BRIDGE" in result.stdout


def test_bridge_list_channels():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0


def test_bridge_channels_list():
    result = runner.invoke(app, ["channels", "list"])
    assert result.exit_code == 0


def test_bridge_inbox_requires_identity():
    result = runner.invoke(app, ["inbox"])
    assert result.exit_code != 0


def test_bridge_inbox_with_identity():
    result = runner.invoke(app, ["inbox", "--as", "test-agent"])
    assert result.exit_code == 0


def test_send_creates_missing_channel():
    result = runner.invoke(app, ["send", "test-channel", "hello", "--as", "test-agent"])
    assert result.exit_code == 0


def test_bridge_recv_requires_identity():
    result = runner.invoke(app, ["recv", "test-channel"])
    assert result.exit_code != 0


def test_bridge_export_channel():
    """Export channel returns markdown format."""
    # First create a channel with a message
    runner.invoke(app, ["send", "export-test", "hello world", "--as", "alice"])

    # Export it
    result = runner.invoke(app, ["export", "export-test"])
    assert result.exit_code == 0
    assert "export-test" in result.stdout
    assert "hello world" in result.stdout

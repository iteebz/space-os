from typer.testing import CliRunner

from space.bridge.app import app

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

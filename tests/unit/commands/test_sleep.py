from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from space.bridge.api import channels as bridge_channels
from space.cli import app
from space.memory import db as memory_db

runner = CliRunner()


def test_sleep_smoketest():
    with (
        patch.object(bridge_channels, "inbox_channels") as mock_inbox_channels,
        patch("space.commands.sleep._get_git_status") as mock_get_git_status,
        patch.object(memory_db, "get_entries") as mock_get_entries,
    ):
        mock_channel = MagicMock()
        mock_channel.name = "test-channel-1"
        mock_inbox_channels.return_value = [mock_channel]
        mock_get_git_status.return_value = "M  file.txt"
        mock_get_entries.return_value = []

        result = runner.invoke(app, ["sleep", "--as", "test-agent"])
        assert result.exit_code == 0
        assert "Running sleep for test-agent..." in result.stdout
        assert "💀 Clean death. Next self thanks you." in result.stdout
        mock_inbox_channels.assert_called_once_with("test-agent")


def test_space_sleep_checkpoint_flow(test_space):
    with (
        patch.object(bridge_channels, "inbox_channels") as mock_inbox_channels,
        patch("space.commands.sleep._get_git_status") as mock_get_git_status,
    ):
        mock_channel = MagicMock()
        mock_channel.name = "test-channel-1"
        mock_inbox_channels.return_value = [mock_channel]
        mock_get_git_status.return_value = "M  file.txt"

        identity = "test-zealot"
        result = runner.invoke(app, ["sleep", "--as", identity])
        assert result.exit_code == 0

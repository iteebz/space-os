from unittest.mock import ANY, MagicMock, patch

from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_wake_command_success(test_space):
    """Verify that the 'space wake' command runs successfully and prints the expected output (no unread messages)."""
    with (
        patch("space.events.identify") as mock_identify,
        patch("space.memory.display.show_wake_summary"),
        patch("space.bridge.api.channels.inbox_channels", return_value=[]),
    ):
        result = runner.invoke(app, ["wake", "--as", "test-agent"])
        assert result.exit_code == 0
        assert "Waking up test-agent" in result.stdout
        assert "🆕 First spawn." in result.stdout
        mock_identify.assert_called_once_with("test-agent", "wake", ANY)


def test_command_unread_messages(test_space):
    """Verify that the 'space wake' command correctly displays unread messages."""
    mock_channel1 = MagicMock()
    mock_channel1.name = "channel-alpha"
    mock_channel1.unread_count = 2

    mock_channel2 = MagicMock()
    mock_channel2.name = "channel-beta"
    mock_channel2.unread_count = 1

    with (
        patch("space.events.identify") as mock_identify,
        patch("space.memory.display.show_wake_summary") as mock_show_wake_summary,
        patch(
            "space.bridge.api.channels.inbox_channels", return_value=[mock_channel1, mock_channel2]
        ) as mock_inbox_channels,
    ):
        # Simulate a previous spawn to ensure _show_orientation is called
        runner.invoke(app, ["wake", "--as", "test-agent"])
        result = runner.invoke(app, ["wake", "--as", "test-agent"])
        assert result.exit_code == 0
        assert "Waking up test-agent" in result.stdout
        assert "📬 3 messages in 2 channels:" in result.stdout
        assert "  #channel-alpha (2 unread)" in result.stdout
        assert "  #channel-beta (1 unread)" in result.stdout
        assert "bridge recv <channel> --as test-agent" in result.stdout
        mock_identify.assert_called_with("test-agent", "wake", ANY)
        mock_show_wake_summary.assert_called_once_with(identity="test-agent", quiet_output=False)
        mock_inbox_channels.assert_called_once_with("test-agent")
    assert result.exit_code == 0

"""Integration tests for async mention processing."""

from unittest.mock import patch

from typer.testing import CliRunner

from space.bridge.app import app

runner = CliRunner()


@patch("space.bridge.api.messages.subprocess.Popen")
@patch("space.bridge.api.messages.db.get_channel_name")
@patch("space.bridge.api.messages.db.create_message")
@patch("space.bridge.api.messages.registry.ensure_agent")
def test_api_spawns_worker_on_mention(mock_ensure, mock_create, mock_get_ch, mock_popen):
    """API layer spawns worker subprocess when @mention detected."""
    mock_ensure.return_value = "agent-id"
    mock_get_ch.return_value = "test-channel"

    result = runner.invoke(
        app, ["send", "test-channel", "@hailot do something", "--as", "user", "--quiet"]
    )

    assert result.exit_code == 0

    # Verify worker subprocess was spawned
    mock_popen.assert_called_once()
    popen_args = mock_popen.call_args[0][0]
    assert "space.bridge.worker" in " ".join(popen_args)
    assert "@hailot do something" in popen_args


@patch("space.bridge.api.messages.subprocess.Popen")
@patch("space.bridge.api.messages.db.create_message")
@patch("space.bridge.api.messages.registry.ensure_agent")
def test_api_skips_worker_without_mention(mock_ensure, mock_create, mock_popen):
    """API doesn't spawn worker if no @mention present."""
    mock_ensure.return_value = "agent-id"

    result = runner.invoke(
        app, ["send", "test-channel", "plain message", "--as", "user", "--quiet"]
    )

    assert result.exit_code == 0

    # Worker should not be spawned
    mock_popen.assert_not_called()


@patch("space.bridge.api.messages.subprocess.Popen")
@patch("space.bridge.api.messages.db.create_message")
@patch("space.bridge.api.messages.registry.ensure_agent")
def test_api_skips_worker_for_system_message(mock_ensure, mock_create, mock_popen):
    """API doesn't process system messages for mentions."""
    mock_ensure.return_value = "agent-id"

    from space.bridge.api import messages

    channel_id = "ch123"
    messages.send_message(channel_id, "system", "[system] some event @hailot")

    # Worker should not be spawned for system messages
    mock_popen.assert_not_called()

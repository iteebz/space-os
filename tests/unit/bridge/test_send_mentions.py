from unittest.mock import patch

from typer.testing import CliRunner

from space.bridge.app import app

runner = CliRunner()


@patch("space.bridge.api.messages.subprocess.Popen")
@patch("space.bridge.api.messages.db.create_message")
@patch("space.bridge.api.messages.registry.ensure_agent")
def test_send_with_mentions_spawns_worker(mock_ensure_agent, mock_create_msg, mock_popen):
    """Sending message with @mentions spawns worker process."""
    mock_ensure_agent.return_value = "agent-id"

    result = runner.invoke(
        app, ["send", "test-channel", "@hailot do something", "--as", "test-user", "--quiet"]
    )

    assert result.exit_code == 0

    # Verify worker was spawned
    assert mock_popen.called


@patch("space.bridge.api.messages.subprocess.Popen")
@patch("space.bridge.api.messages.db.create_message")
@patch("space.bridge.api.messages.registry.ensure_agent")
def test_send_no_mentions_skips_worker(mock_ensure_agent, mock_create_msg, mock_popen):
    """Sending regular message doesn't spawn worker."""
    mock_ensure_agent.return_value = "agent-id"

    result = runner.invoke(
        app, ["send", "test-channel", "regular message", "--as", "test-user", "--quiet"]
    )

    assert result.exit_code == 0

    # Verify worker was NOT spawned
    assert not mock_popen.called

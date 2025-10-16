"""Tests for async worker subprocess."""

from unittest.mock import MagicMock, patch

from space.bridge import worker


@patch("space.bridge.worker.api_messages.send_message")
@patch("space.bridge.worker.subprocess.run")
@patch("space.bridge.worker.parser.spawn_from_mention")
@patch("space.bridge.worker.parser.parse_mentions")
def test_worker_spawns_agents(mock_mentions, mock_spawn_mention, mock_run, mock_send_msg):
    """Worker spawns agents and sends results to channel."""
    mock_mentions.return_value = ["hailot"]
    mock_spawn_mention.return_value = "test prompt"

    spawn_result = MagicMock()
    spawn_result.returncode = 0
    spawn_result.stdout = "response from hailot"
    mock_run.return_value = spawn_result

    import sys

    original_argv = sys.argv
    try:
        sys.argv = ["worker", "channel-id", "test-channel", "@hailot do something"]
        worker.main()
    finally:
        sys.argv = original_argv

    # Verify system message was sent
    assert mock_send_msg.call_count == 2
    first_call = mock_send_msg.call_args_list[0]
    assert "[system] spawning 1 agent(s)" in first_call[0][2]

    # Verify hailot response was sent
    second_call = mock_send_msg.call_args_list[1]
    assert second_call[0][1] == "hailot"
    assert "response from hailot" in second_call[0][2]


@patch("space.bridge.worker.parser.parse_mentions")
def test_worker_skips_if_no_mentions(mock_mentions):
    """Worker exits early if no mentions found."""
    mock_mentions.return_value = []

    import sys

    original_argv = sys.argv
    try:
        sys.argv = ["worker", "channel-id", "test-channel", "plain message"]
        result = worker.main()
    finally:
        sys.argv = original_argv

    assert result is None


@patch("space.bridge.worker.api_messages.send_message")
@patch("space.bridge.worker.subprocess.run")
@patch("space.bridge.worker.parser.spawn_from_mention")
@patch("space.bridge.worker.parser.parse_mentions")
def test_worker_handles_spawn_failure(mock_mentions, mock_spawn_mention, mock_run, mock_send_msg):
    """Worker handles spawn returning non-zero exit code."""
    mock_mentions.return_value = ["hailot"]
    mock_spawn_mention.return_value = "test prompt"

    spawn_result = MagicMock()
    spawn_result.returncode = 1  # failure
    mock_run.return_value = spawn_result

    import sys

    original_argv = sys.argv
    try:
        sys.argv = ["worker", "channel-id", "test-channel", "@hailot test"]
        worker.main()
    finally:
        sys.argv = original_argv

    # No system message if no results
    mock_send_msg.assert_not_called()


@patch("space.bridge.worker.api_messages.send_message")
@patch("space.bridge.worker.subprocess.run")
@patch("space.bridge.worker.parser.spawn_from_mention")
@patch("space.bridge.worker.parser.parse_mentions")
def test_worker_handles_spawn_timeout(mock_mentions, mock_spawn_mention, mock_run, mock_send_msg):
    """Worker handles spawn timeout gracefully."""
    import subprocess
    import sys

    mock_mentions.return_value = ["hailot"]
    mock_spawn_mention.return_value = "test prompt"
    mock_run.side_effect = subprocess.TimeoutExpired("spawn", 10)

    original_argv = sys.argv
    try:
        sys.argv = ["worker", "channel-id", "test-channel", "@hailot test"]
        worker.main()
    finally:
        sys.argv = original_argv

    # No system message if timeout
    mock_send_msg.assert_not_called()


@patch("space.bridge.worker.api_messages.send_message")
@patch("space.bridge.worker.subprocess.run")
@patch("space.bridge.worker.parser.spawn_from_mention")
@patch("space.bridge.worker.parser.parse_mentions")
def test_worker_skips_empty_stdout(mock_mentions, mock_spawn_mention, mock_run, mock_send_msg):
    """Worker skips results with empty stdout."""
    mock_mentions.return_value = ["hailot"]
    mock_spawn_mention.return_value = "test prompt"

    spawn_result = MagicMock()
    spawn_result.returncode = 0
    spawn_result.stdout = "   "  # whitespace only
    mock_run.return_value = spawn_result

    import sys

    original_argv = sys.argv
    try:
        sys.argv = ["worker", "channel-id", "test-channel", "@hailot test"]
        worker.main()
    finally:
        sys.argv = original_argv

    # No messages sent for empty output
    mock_send_msg.assert_not_called()

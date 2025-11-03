"""Integration tests for headless spawning (Claude Code ephemeral execution)."""

import pytest

from space.os.bridge.api import channels, messaging
from space.os.spawn.api import agents, launch
from space.lib import store


@pytest.fixture
def test_agent(test_space):
    """Create a test agent."""
    agent_id = agents.register_agent("test-agent", "claude-haiku-4-5", None)
    return agents.get_agent("test-agent")


@pytest.fixture
def test_channel(test_space):
    """Create a test channel."""
    ch = channels.create_channel("test-channel", topic="Test channel for headless spawning")
    return ch


def test_spawn_headless_success(test_agent, test_channel):
    """Test successful headless spawn creates task and posts to bridge."""
    # Mock the subprocess.run call
    import json
    from unittest.mock import MagicMock, patch

    mock_output = {
        "type": "result",
        "subtype": "success",
        "session_id": "test-session-xyz",
        "result": "Hello from Claude",
        "duration_ms": 1000,
    }

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(mock_output), stderr=""
        )

        # Execute headless spawn
        launch.spawn_headless(
            identity="test-agent", task="say hello", channel_id=test_channel.channel_id
        )

    # Verify subprocess was called with correct args
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "claude" in call_args
    assert "--print" in call_args
    assert "say hello" in call_args
    assert "--output-format" in call_args
    assert "json" in call_args


def test_spawn_headless_claude_failure(test_agent, test_channel):
    """Test headless spawn handles Claude failure."""
    from unittest.mock import MagicMock, patch

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Claude error")

        with pytest.raises(RuntimeError, match="Claude spawn failed"):
            launch.spawn_headless(
                identity="test-agent", task="fail", channel_id=test_channel.channel_id
            )


def test_spawn_headless_invalid_agent(test_space):
    """Test headless spawn fails for unknown agent."""
    with pytest.raises(ValueError, match="not found in registry"):
        launch.spawn_headless(identity="unknown", task="test", channel_id="ch-test")


def test_spawn_headless_posts_to_bridge(test_agent, test_channel):
    """Test that headless spawn posts result to bridge channel."""
    import json
    from unittest.mock import MagicMock, patch

    mock_output = {
        "type": "result",
        "subtype": "success",
        "session_id": "test-session-xyz",
        "result": "Test result content",
        "duration_ms": 500,
    }

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(mock_output), stderr=""
        )

        with patch(
            "space.os.bridge.api.messaging.send_message"
        ) as mock_send_message:
            launch.spawn_headless(
                identity="test-agent", task="test task", channel_id=test_channel.channel_id
            )

            # Verify message was posted to bridge
            mock_send_message.assert_called_once()
            call_args = mock_send_message.call_args
            assert call_args[0][0] == test_channel.channel_id  # channel_id
            assert call_args[0][1] == "test-agent"  # identity
            assert "Test result content" in call_args[0][2]  # content

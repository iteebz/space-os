"""Integration tests for ephemeral spawning (Claude Code ephemeral execution)."""

import pytest

from space.os.bridge.api import channels
from space.os.spawn.api import agents, launch


@pytest.fixture
def test_agent(test_space):
    """Create a test agent."""
    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    return agents.get_agent("test-agent")


@pytest.fixture
def test_channel(test_space):
    """Create a test channel."""
    return channels.create_channel("test-channel", topic="Test channel for ephemeral spawning")


@pytest.fixture
def successful_spawn_output():
    """Mock successful subprocess output."""
    return {
        "type": "result",
        "subtype": "success",
        "session_id": "test-session-xyz",
        "result": "Hello from Claude",
        "duration_ms": 1000,
    }


def test_spawn_ephemeral_success(test_agent, test_channel, successful_spawn_output):
    """Test successful ephemeral spawn executes without error."""
    import json
    from unittest.mock import MagicMock, patch

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(successful_spawn_output), stderr=""
        )
        launch.spawn_ephemeral(
            identity="test-agent", instruction="say hello", channel_id=test_channel.channel_id
        )


def test_spawn_ephemeral_claude_failure(test_agent, test_channel):
    """Test ephemeral spawn handles Claude failure."""
    from unittest.mock import MagicMock, patch

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Claude error")

        with pytest.raises(RuntimeError, match="Claude spawn failed"):
            launch.spawn_ephemeral(
                identity="test-agent", instruction="fail", channel_id=test_channel.channel_id
            )


def test_spawn_ephemeral_invalid_agent(test_space):
    """Test ephemeral spawn fails for unknown agent."""
    with pytest.raises(ValueError, match="not found in registry"):
        launch.spawn_ephemeral(identity="unknown", instruction="test", channel_id="ch-test")


def test_spawn_ephemeral_links_session(test_agent, test_channel, successful_spawn_output):
    """Test that ephemeral spawn with session_id succeeds."""
    import json
    from unittest.mock import MagicMock, patch

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(successful_spawn_output), stderr=""
        )
        launch.spawn_ephemeral(
            identity="test-agent", instruction="test task", channel_id=test_channel.channel_id
        )

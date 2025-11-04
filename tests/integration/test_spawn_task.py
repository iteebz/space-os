"""Integration tests for task-based spawning (Claude Code ephemeral execution)."""

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
    return channels.create_channel("test-channel", topic="Test channel for task-based spawning")


def test_spawn_task_success(test_agent, test_channel):
    """Test successful task spawn creates task and links session."""
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
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_output), stderr="")

        # Execute task spawn
        launch.spawn_task(
            identity="test-agent", task="say hello", channel_id=test_channel.channel_id
        )

    # Verify subprocess was called with correct args
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "claude" in call_args
    assert "--dangerously-skip-permissions" in call_args
    assert "--output-format" in call_args
    assert "json" in call_args
    # Context is passed via stdin, not as argument
    call_kwargs = mock_run.call_args[1]
    assert "input" in call_kwargs
    assert "say hello" in call_kwargs["input"]


def test_spawn_task_claude_failure(test_agent, test_channel):
    """Test task spawn handles Claude failure."""
    from unittest.mock import MagicMock, patch

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Claude error")

        with pytest.raises(RuntimeError, match="Claude spawn failed"):
            launch.spawn_task(
                identity="test-agent", task="fail", channel_id=test_channel.channel_id
            )


def test_spawn_task_invalid_agent(test_space):
    """Test task spawn fails for unknown agent."""
    with pytest.raises(ValueError, match="not found in registry"):
        launch.spawn_task(identity="unknown", task="test", channel_id="ch-test")


def test_spawn_task_links_session(test_agent, test_channel):
    """Test that task spawn links session_id to spawn record."""
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
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_output), stderr="")

        # Spawn task (will attempt to link session_id via linker)
        launch.spawn_task(
            identity="test-agent", task="test task", channel_id=test_channel.channel_id
        )

        # Verify subprocess was called (actual linking is tested in linker tests)
        mock_run.assert_called_once()

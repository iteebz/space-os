"""Integration tests for ephemeral spawning (Claude Code ephemeral execution)."""

from unittest.mock import MagicMock, patch

import pytest

from space.os.bridge.api import channels
from space.os.spawn.api import agents, launch, spawns


@pytest.fixture
def test_agent(test_space):
    """Create a test agent."""
    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    return agents.get_agent("test-agent")


@pytest.fixture
def test_channel(test_space):
    """Create a test channel."""
    return channels.create_channel("test-channel", topic="Test channel for ephemeral spawning")


def test_spawn_ephemeral_claude_streams_ingest(test_agent, test_channel):
    """Contract: session autodiscovery attempts post-spawn discovery."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.communicate.return_value = ("Response text", "")
    mock_proc.returncode = 0

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("space.os.sessions.api.linker.link_spawn_to_session") as mock_link:
            with patch(
                "space.lib.providers.Claude.discover_session", return_value="test-session-id"
            ):
                launch.spawn_ephemeral(
                    identity="test-agent",
                    instruction="test",
                    channel_id=test_channel.channel_id,
                )

                mock_link.assert_called_once()


def test_spawn_ephemeral_claude_extracts_session_once(test_agent, test_channel):
    """Contract: explicit resume links to provided session."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.communicate.return_value = ("Response", "")
    mock_proc.returncode = 0

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("space.os.sessions.api.linker.link_spawn_to_session") as mock_link:
            with patch("space.os.spawn.api.launch.resolve_session_id") as mock_resolve:
                with patch("space.os.bridge.api.messaging.send_message"):
                    mock_resolve.return_value = "sess-claude-456"
                    launch.spawn_ephemeral(
                        identity="test-agent",
                        instruction="test",
                        channel_id=test_channel.channel_id,
                        resume="sess-claude-456",
                    )

                    assert mock_link.call_count == 1
                    args, _ = mock_link.call_args
                    assert args[1] == "sess-claude-456"


def test_spawn_ephemeral_no_session_id_raises(test_agent, test_channel):
    """Contract: Succeeds even if no session discovered (session linking is optional)."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.communicate.return_value = ("Response", "")
    mock_proc.returncode = 0

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("space.os.spawn.api.launch._discover_recent_session") as mock_discover:
            with patch("space.os.bridge.api.messaging.send_message"):
                mock_discover.return_value = None
                launch.spawn_ephemeral(
                    identity="test-agent",
                    instruction="test",
                    channel_id=test_channel.channel_id,
                )


def test_spawn_ephemeral_process_failure_raises(test_agent, test_channel):
    """Contract: Raises RuntimeError when subprocess returns non-zero."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.communicate.return_value = ("", "Process error")
    mock_proc.returncode = 1

    with patch("subprocess.Popen", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="spawn failed"):
            launch.spawn_ephemeral(
                identity="test-agent",
                instruction="test",
                channel_id=test_channel.channel_id,
            )


def test_spawn_ephemeral_ingest_graceful_failure(test_agent, test_channel):
    """Contract: session discovery failures are graceful."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.communicate.return_value = ("Response", "")
    mock_proc.returncode = 0

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch(
            "space.os.spawn.api.launch._discover_recent_session",
            side_effect=Exception("discovery failed"),
        ):
            with patch("space.os.bridge.api.messaging.send_message"):
                launch.spawn_ephemeral(
                    identity="test-agent", instruction="test", channel_id=test_channel.channel_id
                )


def test_spawn_depth_limit_enforced(test_agent, test_channel, monkeypatch):
    """Contract: Spawn rejected when parent depth >= MAX_SPAWN_DEPTH."""
    root = spawns.create_spawn(test_agent.agent_id)
    child1 = spawns.create_spawn(test_agent.agent_id, parent_spawn_id=root.id)
    child2 = spawns.create_spawn(test_agent.agent_id, parent_spawn_id=child1.id)
    child3 = spawns.create_spawn(test_agent.agent_id, parent_spawn_id=child2.id)

    monkeypatch.setenv("SPACE_SPAWN_ID", child3.id)

    with pytest.raises(ValueError, match="max depth"):
        launch.spawn_ephemeral(
            identity="test-agent", instruction="test", channel_id=test_channel.channel_id
        )

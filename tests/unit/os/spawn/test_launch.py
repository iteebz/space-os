"""Integration tests for ephemeral spawning (Claude Code ephemeral execution)."""

import json
from unittest.mock import MagicMock, patch

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


def test_spawn_ephemeral_claude_streams_ingest(test_agent, test_channel):
    """Contract: ingest() called on every stdout line after session_id extracted."""
    stream_output = [
        json.dumps({"session_id": "sess-claude-123"}),
        json.dumps({"event": "processing"}),
        json.dumps({"event": "done"}),
    ]

    mock_proc = MagicMock()
    mock_proc.stdout = stream_output
    mock_proc.returncode = 0
    mock_proc.wait = MagicMock()
    mock_proc.kill = MagicMock()

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("space.os.sessions.api.linker.link_spawn_to_session") as mock_link:
            with patch("space.os.sessions.api.sync.ingest") as mock_ingest:
                launch.spawn_ephemeral(
                    identity="test-agent", instruction="test", channel_id=test_channel.channel_id
                )

                mock_link.assert_called_once()
                assert mock_ingest.call_count == 3


def test_spawn_ephemeral_claude_extracts_session_once(test_agent, test_channel):
    """Contract: session_id extracted exactly once from first event."""
    stream_output = [
        json.dumps({"session_id": "sess-claude-456"}),
        json.dumps({"event": "line2"}),
    ]

    mock_proc = MagicMock()
    mock_proc.stdout = stream_output
    mock_proc.returncode = 0
    mock_proc.wait = MagicMock()

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("space.os.sessions.api.linker.link_spawn_to_session") as mock_link:
            with patch("space.os.sessions.api.sync.ingest"):
                launch.spawn_ephemeral(
                    identity="test-agent", instruction="test", channel_id=test_channel.channel_id
                )

                assert mock_link.call_count == 1
                args, _ = mock_link.call_args
                assert args[1] == "sess-claude-456"


def test_spawn_ephemeral_no_session_id_raises(test_agent, test_channel):
    """Contract: Raises RuntimeError if no session_id found in output stream."""
    stream_output = [
        json.dumps({"event": "no_session_id"}),
    ]

    mock_proc = MagicMock()
    mock_proc.stdout = stream_output
    mock_proc.returncode = 0
    mock_proc.wait = MagicMock()

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("space.os.sessions.api.linker.link_spawn_to_session"):
            with patch("space.os.sessions.api.sync.ingest"):
                with pytest.raises(RuntimeError, match="No session_id"):
                    launch.spawn_ephemeral(
                        identity="test-agent",
                        instruction="test",
                        channel_id=test_channel.channel_id,
                    )


def test_spawn_ephemeral_process_failure_raises(test_agent, test_channel):
    """Contract: Raises RuntimeError when subprocess returns non-zero."""
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = "Process error"

    mock_proc = MagicMock()
    mock_proc.stdout = [json.dumps({"session_id": "sess-test"})]
    mock_proc.returncode = 1
    mock_proc.stderr = mock_stderr
    mock_proc.wait = MagicMock()
    mock_proc.kill = MagicMock()

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("space.os.sessions.api.linker.link_spawn_to_session"):
            with patch("space.os.sessions.api.sync.ingest"):
                with pytest.raises(RuntimeError, match="spawn failed"):
                    launch.spawn_ephemeral(
                        identity="test-agent",
                        instruction="test",
                        channel_id=test_channel.channel_id,
                    )


def test_spawn_ephemeral_ingest_graceful_failure(test_agent, test_channel):
    """Contract: ingest() failures are graceful (caught and passed)."""
    stream_output = [
        json.dumps({"session_id": "sess-test-999"}),
        json.dumps({"event": "processing"}),
    ]

    mock_proc = MagicMock()
    mock_proc.stdout = stream_output
    mock_proc.returncode = 0
    mock_proc.wait = MagicMock()

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("space.os.sessions.api.linker.link_spawn_to_session"):
            with patch("space.os.sessions.api.sync.ingest", side_effect=Exception("ingest failed")):
                launch.spawn_ephemeral(
                    identity="test-agent", instruction="test", channel_id=test_channel.channel_id
                )


def test_spawn_ephemeral_timeout_raises(test_agent, test_channel):
    """Contract: TimeoutExpired is caught and raises RuntimeError."""
    import subprocess

    mock_proc = MagicMock()
    mock_proc.stdout = []
    mock_proc.wait = MagicMock(side_effect=subprocess.TimeoutExpired("claude", 300))
    mock_proc.kill = MagicMock()

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("space.os.sessions.api.linker.link_spawn_to_session"):
            with patch("space.os.sessions.api.sync.ingest"):
                with pytest.raises(RuntimeError, match="timed out"):
                    launch.spawn_ephemeral(
                        identity="test-agent",
                        instruction="test",
                        channel_id=test_channel.channel_id,
                    )

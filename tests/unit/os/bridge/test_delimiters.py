"""Unit tests for bridge delimiter parsing and prompt building."""

import time
from unittest.mock import MagicMock, patch

from space.core.models import Agent
from space.os.bridge.api import delimiters
from space.os.spawn.api.prompt import build_spawn_context


def test_parse_mentions_single():
    """Extract single @mention."""
    content = "@zealot can you help?"
    parsed = delimiters._parse_mentions(content)
    assert parsed == ["zealot"]


def test_parse_mentions_multiple():
    """Extract multiple @mentions."""
    content = "@zealot @sentinel what do you think?"
    parsed = delimiters._parse_mentions(content)
    assert set(parsed) == {"zealot", "sentinel"}


def test_parse_mentions_no_duplicates():
    """Deduplicate mentions."""
    content = "@zealot please respond. @zealot are you there?"
    parsed = delimiters._parse_mentions(content)
    assert parsed == ["zealot"]


def test_parse_mentions_none():
    """No mentions in content."""
    content = "just a regular message"
    parsed = delimiters._parse_mentions(content)
    assert parsed == []


def test_build_spawn_context_interactive():
    """Build spawn context for interactive mode."""
    with patch("space.os.spawn.api.prompt.agents.get_agent") as mock_get_agent:
        mock_agent = Agent(
            agent_id="a-1",
            identity="zealot",
            constitution="zealot.md",
            model="claude-haiku-4-5",
            created_at="2024-01-01",
        )
        mock_get_agent.return_value = mock_agent

        result = build_spawn_context("zealot")

        assert result is not None
        assert "You are zealot" in result
        assert "PRIMITIVES" in result
        assert "AGENT DISCOVERY" in result


def test_build_spawn_context_with_task():
    """Build spawn context with task instruction."""
    with patch("space.os.spawn.api.prompt.agents.get_agent") as mock_get_agent:
        mock_agent = Agent(
            agent_id="a-1",
            identity="zealot",
            constitution="zealot.md",
            model="claude-haiku-4-5",
            created_at="2024-01-01",
        )
        mock_get_agent.return_value = mock_agent

        result = build_spawn_context("zealot", task="analyze this bug")

        assert result is not None
        assert "You are zealot" in result
        assert "PRIMITIVES" in result
        assert "analyze this bug" in result
        assert "TASK:" in result


def test_build_spawn_context_with_channel():
    """Build spawn context with channel context."""
    with patch("space.os.spawn.api.prompt.agents.get_agent") as mock_get_agent:
        mock_agent = Agent(
            agent_id="a-1",
            identity="zealot",
            constitution="zealot.md",
            model="claude-haiku-4-5",
            created_at="2024-01-01",
        )
        mock_get_agent.return_value = mock_agent

        result = build_spawn_context("zealot", task="respond here", channel="bugs")

        assert result is not None
        assert "You are zealot" in result
        assert "CHANNEL: #bugs" in result
        assert "respond here" in result


def test_spawn_from_mentions_enqueues_work():
    """Verify spawn_from_mentions enqueues work to bounded queue."""
    # Reset queue state
    while not delimiters._spawn_queue.empty():
        delimiters._spawn_queue.get_nowait()

    delimiters.spawn_from_mentions("test-channel", "@zealot do something", "agent-123")

    # Verify item was enqueued
    assert delimiters._spawn_queue.qsize() == 1

    # Verify worker thread started
    assert delimiters._worker_thread is not None
    assert delimiters._worker_thread.is_alive()


def test_worker_processes_queue():
    """Verify worker thread processes queued items."""
    # Reset queue
    while not delimiters._spawn_queue.empty():
        delimiters._spawn_queue.get_nowait()

    # Mock dependencies (channels is imported inside worker, so patch at import path)
    with (
        patch("space.os.bridge.api.channels.get_channel") as mock_get_channel,
        patch("space.os.bridge.api.delimiters._process_control_commands_impl") as mock_control,
        patch("space.os.bridge.api.delimiters._process_mentions") as mock_mentions,
    ):
        mock_channel = MagicMock()
        mock_channel.channel_id = "test-ch"
        mock_get_channel.return_value = mock_channel

        # Enqueue work
        delimiters.spawn_from_mentions("test-ch", "@zealot test", "agent-1")

        # Wait for worker to process (max 2 seconds)
        start = time.time()
        while delimiters._spawn_queue.qsize() > 0 and (time.time() - start) < 2:
            time.sleep(0.1)

        # Verify processing happened
        assert delimiters._spawn_queue.qsize() == 0
        mock_control.assert_called_once_with("test-ch", "@zealot test")
        mock_mentions.assert_called_once_with("test-ch", "@zealot test", "agent-1")

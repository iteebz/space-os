"""Unit tests for bridge delimiter parsing and prompt building."""

from unittest.mock import MagicMock, patch

import pytest

from space.core.models import Agent
from space.os.bridge import control, delimiters, mentions
from space.os.spawn.prompt import build_spawn_context


def test_parse_mentions_single():
    """Extract single @mention."""
    content = "@zealot can you help?"
    parsed = mentions.extract_mentions(content)
    assert parsed == ["zealot"]


def test_parse_mentions_multiple():
    """Extract multiple @mentions."""
    content = "@zealot @sentinel what do you think?"
    parsed = mentions.extract_mentions(content)
    assert set(parsed) == {"zealot", "sentinel"}


def test_parse_mentions_no_duplicates():
    """Deduplicate mentions."""
    content = "@zealot please respond. @zealot are you there?"
    parsed = mentions.extract_mentions(content)
    assert parsed == ["zealot"]


def test_parse_mentions_none():
    """No mentions in content."""
    content = "just a regular message"
    parsed = mentions.extract_mentions(content)
    assert parsed == []


def test_build_spawn_context_basic():
    """Build spawn context with agent identity."""
    with patch("space.os.spawn.prompt.agents.get_agent") as mock_get_agent:
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
        assert "task list" in result


def test_build_spawn_context_with_task():
    """Build spawn context with task instruction."""
    with patch("space.os.spawn.prompt.agents.get_agent") as mock_get_agent:
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
    with patch("space.os.spawn.prompt.agents.get_agent") as mock_get_agent:
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


def test_process_control_commands_stop():
    """Slash command processor stops running spawns."""
    with (
        patch("space.os.bridge.control.spawn_agents.get_agent") as mock_get_agent,
        patch("space.os.bridge.control.spawns.get_spawns_for_agent") as mock_get_spawns,
        patch("space.os.bridge.control.spawns.terminate_spawn") as mock_terminate,
    ):
        mock_agent = MagicMock()
        mock_agent.agent_id = "agent-123"
        mock_get_agent.return_value = mock_agent

        mock_spawn = MagicMock()
        mock_spawn.id = "spawn-456"
        mock_spawn.status = "running"
        mock_spawn.channel_id = "channel-1"
        mock_get_spawns.return_value = [mock_spawn]

        control.process_control_commands("channel-1", "/stop zealot")

        mock_terminate.assert_called_once_with("spawn-456", "killed")


@pytest.mark.asyncio
async def test_process_delimiters_async():
    """Verify async delimiter processing."""
    with (
        patch("space.os.bridge.channels.get_channel") as mock_get_channel,
        patch("space.os.bridge.delimiters.process_control_commands") as mock_control,
        patch("space.os.bridge.delimiters.process_mentions") as mock_mentions,
        patch("space.os.bridge.delimiters.process_signals") as mock_signals,
    ):
        mock_channel = MagicMock()
        mock_channel.channel_id = "test-ch"
        mock_get_channel.return_value = mock_channel

        await delimiters.process_delimiters("test-ch", "@zealot test", "agent-1")

        mock_control.assert_called_once_with("test-ch", "@zealot test", "agent-1")
        mock_signals.assert_called_once_with("test-ch", "@zealot test", "agent-1")
        mock_mentions.assert_called_once_with("test-ch", "@zealot test", "agent-1")

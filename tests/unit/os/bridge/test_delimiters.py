"""Unit tests for bridge delimiter parsing and prompt building."""

from unittest.mock import MagicMock, patch

import pytest

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


def test_process_control_commands_pause():
    """Control command processor pauses running spawns."""
    from unittest.mock import MagicMock, patch

    with (
        patch("space.os.bridge.api.delimiters.spawn_agents.get_agent") as mock_get_agent,
        patch("space.os.bridge.api.delimiters.spawns.get_spawns_for_agent") as mock_get_spawns,
        patch("space.os.bridge.api.delimiters.spawns.pause_spawn") as mock_pause,
    ):
        # Setup mocks
        mock_agent = MagicMock()
        mock_agent.agent_id = "agent-123"
        mock_get_agent.return_value = mock_agent

        mock_spawn = MagicMock()
        mock_spawn.id = "spawn-456"
        mock_spawn.status = "running"
        mock_get_spawns.return_value = [mock_spawn]

        # Process !zealot command
        delimiters._process_control_commands_impl("channel-1", "!zealot")

        # Verify pause was called
        mock_pause.assert_called_once_with("spawn-456")


def test_process_control_commands_resume():
    """Control command processor resumes paused spawns."""
    with (
        patch("space.os.bridge.api.delimiters.spawn_agents.get_agent") as mock_get_agent,
        patch("space.os.bridge.api.delimiters.spawns.get_spawns_for_agent") as mock_get_spawns,
        patch("space.os.bridge.api.delimiters.spawns.resume_spawn") as mock_resume,
    ):
        mock_agent = MagicMock()
        mock_agent.agent_id = "agent-123"
        mock_get_agent.return_value = mock_agent

        mock_spawn = MagicMock()
        mock_spawn.id = "spawn-456"
        mock_spawn.status = "paused"
        mock_get_spawns.return_value = [mock_spawn]

        # Process !resume zealot command
        delimiters._process_control_commands_impl("channel-1", "!resume zealot")

        # Verify resume was called
        mock_resume.assert_called_once_with("spawn-456")


@pytest.mark.asyncio
async def test_process_delimiters_async():
    """Verify async delimiter processing."""
    with (
        patch("space.os.bridge.api.channels.get_channel") as mock_get_channel,
        patch("space.os.bridge.api.delimiters._process_control_commands_impl") as mock_control,
        patch("space.os.bridge.api.delimiters._process_mentions") as mock_mentions,
    ):
        mock_channel = MagicMock()
        mock_channel.channel_id = "test-ch"
        mock_get_channel.return_value = mock_channel

        await delimiters.process_delimiters("test-ch", "@zealot test", "agent-1")

        mock_control.assert_called_once_with("test-ch", "@zealot test")
        mock_mentions.assert_called_once_with("test-ch", "@zealot test", "agent-1")

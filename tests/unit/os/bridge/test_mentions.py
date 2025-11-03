"""Unit tests for bridge mention parsing and prompt building."""

from unittest.mock import patch

from space.core.models import Agent
from space.os.bridge.api import mentions
from space.os.spawn.api.prompt import build_spawn_context


def test_parse_mentions_single():
    """Extract single @mention."""
    content = "@zealot can you help?"
    parsed = mentions._parse_mentions(content)
    assert parsed == ["zealot"]


def test_parse_mentions_multiple():
    """Extract multiple @mentions."""
    content = "@zealot @sentinel what do you think?"
    parsed = mentions._parse_mentions(content)
    assert set(parsed) == {"zealot", "sentinel"}


def test_parse_mentions_no_duplicates():
    """Deduplicate mentions."""
    content = "@zealot please respond. @zealot are you there?"
    parsed = mentions._parse_mentions(content)
    assert parsed == ["zealot"]


def test_parse_mentions_none():
    """No mentions in content."""
    content = "just a regular message"
    parsed = mentions._parse_mentions(content)
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

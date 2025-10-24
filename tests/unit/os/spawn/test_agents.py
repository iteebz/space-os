"""Unit tests for spawn/agents thin wrappers."""

from unittest.mock import patch

from space.os.core.spawn.agents.claude import Claude
from space.os.core.spawn.agents.codex import Codex
from space.os.core.spawn.agents.gemini import Gemini


def test_claude_init_valid():
    """Claude initializes with identity."""
    agent = Claude("hailot")
    assert agent.identity == "hailot"


def test_claude_run_with_prompt():
    """Claude.run() with prompt calls lib_agents.claude.spawn()."""
    with patch("space.os.lib.agents.claude.spawn", return_value="task output") as mock_spawn:
        agent = Claude("hailot")
        result = agent.run("test prompt")

        assert result == "task output"
        mock_spawn.assert_called_once_with("hailot", "test prompt")


def test_claude_run_no_prompt():
    """Claude.run() with None calls lib_agents.claude.spawn()."""
    with patch("space.os.lib.agents.claude.spawn", return_value="") as mock_spawn:
        agent = Claude("hailot")
        result = agent.run(None)

        assert result == ""
        mock_spawn.assert_called_once_with("hailot", None)


def test_gemini_init_valid():
    """Gemini initializes with identity."""
    agent = Gemini("zealot")
    assert agent.identity == "zealot"


def test_gemini_run_with_prompt():
    """Gemini.run() with prompt calls lib_agents.gemini.spawn()."""
    with patch("space.os.lib.agents.gemini.spawn", return_value="gemini output") as mock_spawn:
        agent = Gemini("zealot")
        result = agent.run("analyze this")

        assert result == "gemini output"
        mock_spawn.assert_called_once_with("zealot", "analyze this")


def test_codex_init_valid():
    """Codex initializes with identity."""
    agent = Codex("hailot")
    assert agent.identity == "hailot"


def test_codex_run_with_prompt():
    """Codex.run() with prompt calls lib_agents.codex.spawn()."""
    with patch("space.os.lib.agents.codex.spawn", return_value="codex output") as mock_spawn:
        agent = Codex("hailot")
        result = agent.run("code this")

        assert result == "codex output"
        mock_spawn.assert_called_once_with("hailot", "code this")

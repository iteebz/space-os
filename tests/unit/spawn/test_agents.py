"""Unit tests for agent classes: config loading and error handling."""

from unittest.mock import MagicMock, patch

import pytest

from space.spawn.agents.claude import Claude
from space.spawn.agents.codex import Codex
from space.spawn.agents.gemini import Gemini


@pytest.fixture
def valid_cfg():
    """Valid config with roles and agents."""
    return {
        "roles": {
            "hailot": {"base_identity": "claude", "constitution": "/path/to/hailot.md"},
            "zealot": {"base_identity": "gemini", "constitution": "/path/to/zealot.md"},
        },
        "agents": {
            "claude": {"model": "claude-4", "command": "claude-code"},
            "gemini": {"model": "gemini-2.5-pro", "command": "gemini-code"},
            "codex": {"model": "codex", "command": "codex-code"},
        },
    }


def test_claude_init_valid(valid_cfg):
    """Claude initializes with valid config."""
    with (
        patch("space.spawn.agents.claude.config.init_config"),
        patch("space.spawn.agents.claude.config.load_config", return_value=valid_cfg),
    ):
        agent = Claude("hailot")
        assert agent.identity == "hailot"
        assert agent.base_identity == "claude"
        assert agent.model == "claude-4"
        assert agent.command == "claude-code"


def test_claude_init_unknown_identity(valid_cfg):
    """Claude raises on unknown identity."""
    with (
        patch("space.spawn.agents.claude.config.init_config"),
        patch("space.spawn.agents.claude.config.load_config", return_value=valid_cfg),
    ):
        with pytest.raises(ValueError, match="Unknown identity"):
            Claude("nonexistent")


def test_claude_init_missing_agent_config(valid_cfg):
    """Claude raises when agent not in config."""
    cfg = valid_cfg.copy()
    cfg["agents"] = {}
    with (
        patch("space.spawn.agents.claude.config.init_config"),
        patch("space.spawn.agents.claude.config.load_config", return_value=cfg),
    ):
        with pytest.raises(ValueError, match="Agent not configured"):
            Claude("hailot")


def test_claude_run_with_prompt():
    """Claude.run() with prompt executes _task."""
    with (
        patch("space.spawn.agents.claude.config.init_config"),
        patch("space.spawn.agents.claude.config.load_config") as mock_load,
        patch("space.spawn.agents.claude.subprocess.run") as mock_run,
    ):
        mock_load.return_value = {
            "roles": {"hailot": {"base_identity": "claude", "constitution": "c.md"}},
            "agents": {"claude": {"model": "claude-4", "command": "claude-code"}},
        }
        mock_run.return_value = MagicMock(stdout="task output", returncode=0)

        agent = Claude("hailot")
        result = agent.run("test prompt")

        assert result == "task output"
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "claude-code" in call_args
        assert "-p" in call_args
        assert "test prompt" in call_args


def test_claude_run_no_prompt():
    """Claude.run() with None launches interactive."""
    with (
        patch("space.spawn.agents.claude.config.init_config"),
        patch("space.spawn.agents.claude.config.load_config") as mock_load,
        patch("space.spawn.spawn.launch_agent") as mock_launch,
    ):
        mock_load.return_value = {
            "roles": {"hailot": {"base_identity": "claude", "constitution": "c.md"}},
            "agents": {"claude": {"model": "claude-4", "command": "claude-code"}},
        }

        agent = Claude("hailot")
        result = agent.run(None)

        assert result == ""
        mock_launch.assert_called_once()


def test_gemini_init_valid(valid_cfg):
    """Gemini initializes with valid config."""
    with (
        patch("space.spawn.agents.gemini.config.init_config"),
        patch("space.spawn.agents.gemini.config.load_config", return_value=valid_cfg),
    ):
        agent = Gemini("zealot")
        assert agent.identity == "zealot"
        assert agent.base_identity == "gemini"
        assert agent.model == "gemini-2.5-pro"
        assert agent.command == "gemini-code"


def test_gemini_init_unknown_identity(valid_cfg):
    """Gemini raises on unknown identity."""
    with (
        patch("space.spawn.agents.gemini.config.init_config"),
        patch("space.spawn.agents.gemini.config.load_config", return_value=valid_cfg),
    ):
        with pytest.raises(ValueError, match="Unknown identity"):
            Gemini("nonexistent")


def test_gemini_run_with_prompt():
    """Gemini.run() with prompt executes _task."""
    with (
        patch("space.spawn.agents.gemini.config.init_config"),
        patch("space.spawn.agents.gemini.config.load_config") as mock_load,
        patch("space.spawn.agents.gemini.subprocess.run") as mock_run,
        patch("space.spawn.spawn.launch_agent"),
    ):
        mock_load.return_value = {
            "roles": {"zealot": {"base_identity": "gemini", "constitution": "z.md"}},
            "agents": {"gemini": {"model": "gemini-2.5-pro", "command": "gemini-code"}},
        }
        mock_run.return_value = MagicMock(stdout="gemini output", returncode=0)

        agent = Gemini("zealot")
        result = agent.run("analyze this")

        assert result == "gemini output"
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gemini-code" in call_args


def test_codex_init_valid(valid_cfg):
    """Codex initializes with valid config."""
    with (
        patch("space.spawn.agents.codex.config.init_config"),
        patch("space.spawn.agents.codex.config.load_config", return_value=valid_cfg),
    ):
        agent = Codex("hailot")
        assert agent.identity == "hailot"
        assert agent.base_identity == "claude"
        assert agent.model == "claude-4"
        assert agent.command == "claude-code"


def test_codex_run_with_prompt():
    """Codex.run() with prompt executes _task."""
    with (
        patch("space.spawn.agents.codex.config.init_config"),
        patch("space.spawn.agents.codex.config.load_config") as mock_load,
        patch("space.spawn.agents.codex.subprocess.run") as mock_run,
        patch("space.spawn.spawn.launch_agent"),
    ):
        mock_load.return_value = {
            "roles": {"hailot": {"base_identity": "claude", "constitution": "c.md"}},
            "agents": {"claude": {"model": "claude-4", "command": "claude-code"}},
        }
        mock_run.return_value = MagicMock(stdout="codex output", returncode=0)

        agent = Codex("hailot")
        result = agent.run("code this")

        assert result == "codex output"

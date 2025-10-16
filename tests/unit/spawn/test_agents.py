import pytest
from unittest.mock import patch, MagicMock

from space.spawn.agents.claude import Claude
from space.spawn.agents.gemini import Gemini
from space.spawn.agents.codex import Codex


@pytest.fixture
def mock_config():
    with patch("space.spawn.agents.claude.config") as cfg:
        cfg.init_config.return_value = None
        cfg.load_config.return_value = {
            "roles": {
                "hailot": {
                    "constitution": "zealot.md",
                    "base_identity": "haiku",
                }
            },
            "agents": {
                "haiku": {
                    "command": "claude",
                    "model": "claude-haiku-4-5",
                }
            },
        }
        yield cfg


def test_claude_init(mock_config):
    agent = Claude("hailot")
    assert agent.identity == "hailot"
    assert agent.model == "claude-haiku-4-5"
    assert agent.command == "claude"


def test_claude_init_unknown_identity(mock_config):
    mock_config.load_config.return_value = {
        "roles": {},
        "agents": {},
    }
    with pytest.raises(ValueError, match="Unknown identity"):
        Claude("unknown")


@patch("subprocess.run")
def test_claude_task(mock_run):
    mock_run.return_value = MagicMock(stdout="task output", stderr="")

    with patch("space.spawn.agents.claude.config") as cfg:
        cfg.init_config.return_value = None
        cfg.load_config.return_value = {
            "roles": {
                "hailot": {
                    "constitution": "zealot.md",
                    "base_identity": "haiku",
                }
            },
            "agents": {
                "haiku": {
                    "command": "claude",
                    "model": "claude-haiku-4-5",
                }
            },
        }

        agent = Claude("hailot")
        result = agent.run("test prompt")

        mock_run.assert_called_once_with(
            ["claude", "-p", "test prompt"],
            capture_output=True,
            text=True,
        )
        assert result == "task output"


@patch("subprocess.run")
def test_gemini_task(mock_run):
    mock_run.return_value = MagicMock(stdout="gemini output", stderr="")

    with patch("space.spawn.agents.gemini.config") as cfg:
        cfg.init_config.return_value = None
        cfg.load_config.return_value = {
            "roles": {
                "harbinger": {
                    "constitution": "harbinger.md",
                    "base_identity": "gemini",
                }
            },
            "agents": {
                "gemini": {
                    "command": "gemini",
                    "model": "gemini-2.5-pro",
                }
            },
        }

        agent = Gemini("harbinger")
        result = agent.run("test prompt")

        mock_run.assert_called_once_with(
            ["gemini", "-p", "test prompt"],
            capture_output=True,
            text=True,
        )
        assert result == "gemini output"


@patch("subprocess.run")
def test_codex_task(mock_run):
    mock_run.return_value = MagicMock(stdout="codex output", stderr="")

    with patch("space.spawn.agents.codex.config") as cfg:
        cfg.init_config.return_value = None
        cfg.load_config.return_value = {
            "roles": {
                "sentinel": {
                    "constitution": "sentinel.md",
                    "base_identity": "codex",
                }
            },
            "agents": {
                "codex": {
                    "command": "codex",
                    "model": "gpt-5-codex",
                }
            },
        }

        agent = Codex("sentinel")
        result = agent.run("test prompt")

        mock_run.assert_called_once_with(
            ["codex", "exec", "test prompt", "--skip-git-repo-check"],
            capture_output=True,
            text=True,
        )
        assert result == "codex output"


def test_claude_interactive():
    with patch("space.spawn.agents.claude.config") as cfg, \
         patch("space.spawn.spawn.launch_agent") as mock_launch:
        cfg.init_config.return_value = None
        cfg.load_config.return_value = {
            "roles": {
                "hailot": {
                    "constitution": "zealot.md",
                    "base_identity": "haiku",
                }
            },
            "agents": {
                "haiku": {
                    "command": "claude",
                    "model": "claude-haiku-4-5",
                }
            },
        }

        agent = Claude("hailot")
        result = agent.run(None)

        mock_launch.assert_called_once()
        assert result == ""

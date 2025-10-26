"""Unit tests for bridge mention parsing and prompt building."""

import subprocess
from unittest.mock import MagicMock, patch

from space.core.bridge.api import mentions


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


def test_build_prompt_success():
    """Build prompt returns prompt for worker to execute."""
    with (
        patch("space.core.bridge.api.mentions.subprocess.run") as mock_run,
        patch("space.core.bridge.api.mentions.config.load_config") as mock_config,
        patch("space.core.bridge.api.mentions.paths.constitution") as mock_const_path,
        patch("space.core.bridge.api.mentions._write_role_file") as mock_write,
    ):
        mock_config.return_value = {
            "roles": {
                "zealot": {
                    "constitution": "zealot.md",
                    "base_agent": "sonnet"
                }
            }
        }
        mock_const_path.return_value.read_text.return_value = "# ZEALOT\nCore principles."
        mock_run.return_value = MagicMock(returncode=0, stdout="# test-channel\n\n[alice] hello\n")

        result = mentions._build_prompt("zealot", "test-channel", "@zealot test message")

        assert result is not None
        assert "You are zealot." in result
        assert "[SPACE INSTRUCTIONS]" in result
        assert "test message" in result
        mock_write.assert_called_once()
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["bridge", "export", "test-channel"]


def test_build_prompt_failure():
    """Failed build prompt returns None."""
    with patch("space.core.bridge.api.mentions.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        result = mentions._build_prompt("zealot", "test-channel", "test")

        assert result is None


def test_build_prompt_timeout():
    """Build prompt timeout returns None gracefully."""
    with patch("space.core.bridge.api.mentions.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("spawn", 120)

        result = mentions._build_prompt("zealot", "test-channel", "test")

        assert result is None

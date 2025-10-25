import subprocess
from unittest.mock import MagicMock, patch

from space.os.core.bridge.ops import spawning


def test_parse_mentions_single():
    """Extract single @mention."""
    content = "@hailot can you help?"
    mentions = spawning._parse_mentions(content)
    assert mentions == ["hailot"]


def test_parse_mentions_multiple():
    """Extract multiple @mentions."""
    content = "@hailot @zealot what do you think?"
    mentions = spawning._parse_mentions(content)
    assert set(mentions) == {"hailot", "zealot"}


def test_parse_mentions_no_duplicates():
    """Deduplicate mentions."""
    content = "@hailot please respond. @hailot are you there?"
    mentions = spawning._parse_mentions(content)
    assert mentions == ["hailot"]


def test_parse_mentions_none():
    """No mentions in content."""
    content = "just a regular message"
    mentions = spawning._parse_mentions(content)
    assert mentions == []


def test_extract_mention_task_simple():
    """Extract task after @mention."""
    content = "@hailot do something"
    task = spawning._extract_mention_task("hailot", content)
    assert task == "do something"


def test_extract_mention_task_with_newlines():
    """Extract task with newlines after @mention."""
    content = "@hailot\nanalyze this situation"
    task = spawning._extract_mention_task("hailot", content)
    assert task == "analyze this situation"


def test_extract_mention_multiple():
    """Extract task stops at next @mention."""
    content = "@hailot do this @zealot do that"
    task = spawning._extract_mention_task("hailot", content)
    assert task == "do this"
    task = spawning._extract_mention_task("zealot", content)
    assert task == "do that"


def test_extract_mention_task_empty():
    """Mention with no task."""
    content = "@hailot"
    task = spawning._extract_mention_task("hailot", content)
    assert task == ""


def test_extract_mention_task_not_found():
    """Identity not mentioned."""
    content = "@zealot do something"
    task = spawning._extract_mention_task("hailot", content)
    assert task == ""


def test_build_prompt_success():
    """Build prompt returns prompt for worker to execute."""
    with (
        patch("space.os.core.bridge.spawning.subprocess.run") as mock_run,
        patch("space.os.core.bridge.spawning.config.load_config") as mock_config,
    ):
        mock_config.return_value = {"roles": {"hailot": {}}}
        mock_run.return_value = MagicMock(returncode=0, stdout="# test-channel\n\n[alice] hello\n")

        result = spawning._build_prompt("hailot", "test-channel", "@hailot test message")

        assert result is not None
        assert "[SPACE INSTRUCTIONS]" in result
        assert "test message" in result
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["bridge", "export", "test-channel"]


def test_build_prompt_failure():
    """Failed build prompt returns None."""
    with patch("space.os.core.bridge.spawning.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        result = spawning._build_prompt("hailot", "test-channel", "test")

        assert result is None


def test_build_prompt_timeout():
    """Build prompt timeout returns None gracefully."""
    with patch("space.os.core.bridge.spawning.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("spawn", 120)

        result = spawning._build_prompt("hailot", "test-channel", "test")

        assert result is None

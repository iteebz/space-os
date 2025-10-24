import subprocess
from unittest.mock import MagicMock, patch

from space.os.bridge import parser


def test_parse_mentions_single():
    """Extract single @mention."""
    content = "@hailot can you help?"
    mentions = parser.parse_mentions(content)
    assert mentions == ["hailot"]


def test_parse_mentions_multiple():
    """Extract multiple @mentions."""
    content = "@hailot @zealot what do you think?"
    mentions = parser.parse_mentions(content)
    assert set(mentions) == {"hailot", "zealot"}


def test_parse_mentions_no_duplicates():
    """Deduplicate mentions."""
    content = "@hailot please respond. @hailot are you there?"
    mentions = parser.parse_mentions(content)
    assert mentions == ["hailot"]


def test_parse_mentions_none():
    """No mentions in content."""
    content = "just a regular message"
    mentions = parser.parse_mentions(content)
    assert mentions == []


def test_should_spawn_valid_role():
    """Check valid role identity."""
    assert parser.should_spawn("hailot", "some content") is True
    assert parser.should_spawn("zealot", "some content") is True


def test_should_spawn_invalid_role():
    """Check invalid role identity."""
    assert parser.should_spawn("nonexistent", "some content") is False
    assert parser.should_spawn("", "some content") is False


def test_extract_mention_task_simple():
    """Extract task after @mention."""
    content = "@hailot do something"
    task = parser.extract_mention_task("hailot", content)
    assert task == "do something"


def test_extract_mention_task_with_newlines():
    """Extract task with newlines after @mention."""
    content = "@hailot\nanalyze this situation"
    task = parser.extract_mention_task("hailot", content)
    assert task == "analyze this situation"


def test_extract_mention_task_multiple_mentions():
    """Extract task stops at next @mention."""
    content = "@hailot do this @zealot do that"
    task = parser.extract_mention_task("hailot", content)
    assert task == "do this"
    task = parser.extract_mention_task("zealot", content)
    assert task == "do that"


def test_extract_mention_task_empty():
    """Mention with no task."""
    content = "@hailot"
    task = parser.extract_mention_task("hailot", content)
    assert task == ""


def test_extract_mention_task_not_found():
    """Identity not mentioned."""
    content = "@zealot do something"
    task = parser.extract_mention_task("hailot", content)
    assert task == ""


def test_spawn_from_mention_success():
    """Spawn from mention returns prompt for worker to execute."""
    with patch("space.os.bridge.parser.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="# test-channel\n\n[alice] hello\n")

        result = parser.spawn_from_mention("hailot", "test-channel", "@hailot test message")

        assert result is not None
        assert "[TASK INSTRUCTIONS]" in result
        assert "test message" in result
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["bridge", "export", "test-channel"]


def test_spawn_from_mention_failure():
    """Failed spawn returns None."""
    with patch("space.os.bridge.parser.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        result = parser.spawn_from_mention("hailot", "test-channel", "test")

        assert result is None


def test_spawn_from_mention_timeout():
    """Spawn timeout returns None gracefully."""
    with patch("space.os.bridge.parser.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("spawn", 120)

        result = parser.spawn_from_mention("hailot", "test-channel", "test")

        assert result is None


def test_process_message_single_mention():
    """Process message detects mentions and returns prompts."""
    with patch("space.os.bridge.parser.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="# test-channel\n\n[alice] hello\n")

        results = parser.process_message("test-channel", "@hailot hello")

        assert len(results) == 1
        assert results[0][0] == "hailot"
        assert "[TASK INSTRUCTIONS]" in results[0][1]


def test_process_message_multiple_mentions():
    """Process multiple mentions in one message."""
    with patch("space.os.bridge.parser.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="# test-channel\n\n[alice] hello\n")

        results = parser.process_message("test-channel", "@hailot @zealot thoughts?")

        assert len(results) == 2
        identities = [r[0] for r in results]
        assert set(identities) == {"hailot", "zealot"}
        for _, prompt in results:
            assert "[TASK INSTRUCTIONS]" in prompt


def test_process_message_skips_invalid():
    """Skip invalid identities in mentions."""
    with patch("space.os.bridge.parser.subprocess.run"):
        results = parser.process_message("test-channel", "@nonexistent @hailot hi")

        assert len(results) <= 1

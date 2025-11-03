"""Unit tests for council formatting and message handling."""

from unittest.mock import MagicMock, patch

from space.apps.council import api as council


def test_styled_applies_colors():
    """_styled wraps text with color codes and resets."""
    result = council._styled("text", council.Colors.CYAN)
    assert council.Colors.CYAN in result
    assert council.Colors.RESET in result
    assert "text" in result


def test_styled_multiple_colors():
    """_styled can apply multiple color codes."""
    result = council._styled("text", council.Colors.BOLD, council.Colors.CYAN)
    assert council.Colors.BOLD in result
    assert council.Colors.CYAN in result
    assert council.Colors.RESET in result


def test_format_message_user():
    """Format user message with prompt prefix."""
    msg = MagicMock()
    msg.agent_id = "human"
    msg.created_at = "2025-10-25T12:30:45"
    msg.content = "hello"

    with patch("space.apps.council.cli.spawn.get_agent") as m_get_agent:
        m_agent = MagicMock()
        m_agent.identity = "alice"
        m_get_agent.return_value = m_agent

        result = council.format_message(msg, is_user=True)
        assert ">" in result
        assert "alice" in result
        assert "hello" in result
        assert "12:30:45" in result


def test_format_message_agent():
    """Format agent message without prompt prefix."""
    msg = MagicMock()
    msg.agent_id = "agent-1"
    msg.created_at = "2025-10-25T12:30:45"
    msg.content = "response"

    with patch("space.apps.council.cli.spawn.get_agent") as m_get_agent:
        m_agent = MagicMock()
        m_agent.identity = "zealot"
        m_get_agent.return_value = m_agent

        result = council.format_message(msg, is_user=False)
        assert ">" not in result
        assert "zealot" in result
        assert "response" in result
        assert "12:30:45" in result


def test_format_message_unknown_agent():
    """Format message with unknown agent_id uses raw ID."""
    msg = MagicMock()
    msg.agent_id = "unknown-id"
    msg.created_at = "2025-10-25T12:30:45"
    msg.content = "text"

    with patch("space.apps.council.cli.spawn.get_agent", return_value=None):
        result = council.format_message(msg, is_user=False)
        assert "unknown-id" in result


def test_format_header_with_topic():
    """Format channel header with topic."""
    result = council.format_header("dev-channel", "Development coordination")
    assert "dev-channel" in result
    assert "Development coordination" in result


def test_format_header_without_topic():
    """Format channel header without topic."""
    result = council.format_header("general")
    assert "general" in result


def test_format_error():
    """Format error message with warning symbol."""
    result = council.format_error("Something failed")
    assert "Something failed" in result
    assert "⚠" in result


def test_council_init():
    """Council initializes with channel name and gets channel ID."""
    with patch("space.apps.council.cli.bridge_api.get_channel") as m_get_channel:
        mock_channel = MagicMock()
        mock_channel.channel_id = "ch-123"
        m_get_channel.return_value = mock_channel

        c = council.Council("test-channel")
        assert c.channel_name == "test-channel"
        assert c.channel_id == "ch-123"
        assert c.running is True
        m_get_channel.assert_called_once_with("test-channel")


def test_council_find_new_messages_start_no_previous():
    """Find new messages start from 0 if no previous messages."""
    with patch("space.apps.council.cli.bridge_api.get_channel") as m_get:
        m_get.return_value = MagicMock(channel_id="ch-123")
        c = council.Council("test-channel")
        c.last_msg_id = None

        msgs = [MagicMock(message_id="id-1"), MagicMock(message_id="id-2")]
        start = c._find_new_messages_start(msgs)
        assert start == 0


def test_council_find_new_messages_start_from_last():
    """Find new messages start from after last processed ID."""
    with patch("space.apps.council.cli.bridge_api.get_channel") as m_get:
        m_get.return_value = MagicMock(channel_id="ch-123")
        c = council.Council("test-channel")
        c.last_msg_id = "id-1"

        msgs = [
            MagicMock(message_id="id-1"),
            MagicMock(message_id="id-2"),
            MagicMock(message_id="id-3"),
        ]
        start = c._find_new_messages_start(msgs)
        assert start == 1


def test_council_find_new_messages_start_not_found():
    """Find new messages returns 0 if last message not in current list."""
    with patch("space.apps.council.cli.bridge_api.get_channel") as m_get:
        m_get.return_value = MagicMock(channel_id="ch-123")
        c = council.Council("test-channel")
        c.last_msg_id = "old-id"

        msgs = [MagicMock(message_id="id-1"), MagicMock(message_id="id-2")]
        start = c._find_new_messages_start(msgs)
        assert start == 0


def test_council_should_add_separator_first_message():
    """No separator for first message."""
    with patch("space.apps.council.cli.bridge_api.get_channel") as m_get:
        m_get.return_value = MagicMock(channel_id="ch-123")
        c = council.Council("test-channel")
        c._last_printed_agent_id = None

        result = c._should_add_separator("agent-1", is_user=False)
        assert result is False


def test_council_should_add_separator_user_message():
    """No separator before user messages."""
    with patch("space.apps.council.cli.bridge_api.get_channel") as m_get:
        m_get.return_value = MagicMock(channel_id="ch-123")
        c = council.Council("test-channel")
        c._last_printed_agent_id = "agent-1"

        result = c._should_add_separator("human", is_user=True)
        assert result is False


def test_council_should_add_separator_different_agent():
    """Add separator when switching between agents."""
    with patch("space.apps.council.cli.bridge_api.get_channel") as m_get:
        m_get.return_value = MagicMock(channel_id="ch-123")
        c = council.Council("test-channel")
        c._last_printed_agent_id = "agent-1"

        result = c._should_add_separator("agent-2", is_user=False)
        assert result is True


def test_council_should_add_separator_same_agent():
    """No separator when same agent continues."""
    with patch("space.apps.council.cli.bridge_api.get_channel") as m_get:
        m_get.return_value = MagicMock(channel_id="ch-123")
        c = council.Council("test-channel")
        c._last_printed_agent_id = "agent-1"

        result = c._should_add_separator("agent-1", is_user=False)
        assert result is False

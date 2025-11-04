"""Unit tests for council."""

from unittest.mock import MagicMock, patch

from space.apps.council import api as council


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

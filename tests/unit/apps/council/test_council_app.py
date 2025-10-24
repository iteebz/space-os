"""Tests for Council class."""

from unittest.mock import Mock, patch

import pytest

from space.apps.council.app import Council


@pytest.fixture
def mock_channel():
    """Mock channel data."""
    return {
        "channel_name": "test-channel",
        "channel_id": "ch-123",
    }


@pytest.fixture
def council_instance(mock_channel):
    """Create a Council instance with mocked API."""
    with patch("space.apps.council.app.api.channels.resolve_channel_id") as mock_resolve:
        mock_resolve.return_value = mock_channel["channel_id"]
        return Council(mock_channel["channel_name"])


@pytest.fixture
def mock_messages():
    """Create mock message objects."""
    msg1 = Mock()
    msg1.agent_id = "agent-1"
    msg1.content = "First message"
    msg1.created_at = "2025-10-24T10:00:00"
    msg1.message_id = "msg-1"

    msg2 = Mock()
    msg2.agent_id = "agent-2"
    msg2.content = "Second message"
    msg2.created_at = "2025-10-24T10:01:00"
    msg2.message_id = "msg-2"

    return [msg1, msg2]


def test_initialization(council_instance, mock_channel):
    """Council initializes with channel."""
    assert council_instance.channel_name == mock_channel["channel_name"]
    assert council_instance.channel_id == mock_channel["channel_id"]
    assert council_instance.running is True
    assert council_instance.last_msg_id is None
    assert len(council_instance.sent_msg_ids) == 0


def test_print_message_formats(council_instance, mock_messages, monkeypatch):
    """_print_message formats identity, timestamp, and prefix."""
    monkeypatch.setattr(
        "space.apps.council.formatter.spawn_db.get_identity",
        lambda x: "alice" if x == "agent-1" else x,
    )

    output = []

    def capture_print(*args, **kwargs):
        if args:
            output.append(args[0])

    with patch("builtins.print", side_effect=capture_print):
        council_instance._print_message(mock_messages[0])

    msg_output = next((o for o in output if "First message" in o), None)
    assert msg_output
    assert "alice" in msg_output


def test_print_message_agent_prefix(council_instance, mock_messages, monkeypatch):
    """_print_message formats agent messages correctly."""
    monkeypatch.setattr(
        "space.apps.council.formatter.spawn_db.get_identity",
        lambda x: "bob" if x == "agent-2" else x,
    )

    output = []

    def capture_print(*args, **kwargs):
        if args:
            output.append(args[0])

    with patch("builtins.print", side_effect=capture_print):
        council_instance._print_message(mock_messages[1])

    msg_output = next((o for o in output if "Second message" in o), None)
    assert msg_output
    assert "bob" in msg_output


def test_print_message_human_prefix(council_instance, monkeypatch):
    """_print_message uses > for human messages."""
    human_msg = Mock()
    human_msg.agent_id = "human"
    human_msg.content = "Input"
    human_msg.created_at = "2025-10-24T10:00:00"

    monkeypatch.setattr(
        "space.apps.council.formatter.spawn_db.get_identity",
        lambda x: "human",
    )

    output = []

    def capture_print(*args, **kwargs):
        if args:
            output.append(args[0])

    with patch("builtins.print", side_effect=capture_print):
        council_instance._print_message(human_msg)

    msg_output = next((o for o in output if "Input" in o), None)
    assert msg_output
    assert ">" in msg_output


def test_print_error_writes_stderr(council_instance):
    """_print_error writes to stderr."""
    output = []

    def capture_print(*args, **kwargs):
        output.append((args, kwargs))

    import sys

    with patch("builtins.print", side_effect=capture_print):
        council_instance._print_error("Test error")

    assert len(output) == 1
    assert "Test error" in output[0][0][0]
    assert output[0][1].get("file") == sys.stderr

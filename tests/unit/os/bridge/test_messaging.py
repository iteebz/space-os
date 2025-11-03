from unittest.mock import MagicMock, patch

import pytest

from space.os import bridge


def make_mock_row(data):
    row = MagicMock()
    row.__getitem__ = lambda self, key: data[key]
    row.keys = lambda: data.keys()
    return row


@pytest.fixture
def mock_db():
    conn = MagicMock()
    with patch("space.lib.store.ensure") as mock_ensure:
        mock_ensure.return_value.__enter__.return_value = conn
        mock_ensure.return_value.__exit__.return_value = None
        conn.execute.return_value.fetchone.return_value = make_mock_row(
            {
                "channel_id": "ch-1",
                "name": "general",
                "topic": None,
                "created_at": "2024-01-01T00:00:00",
            }
        )
        conn.execute.return_value.fetchall.return_value = []
        yield conn


@pytest.fixture
def mock_get_agent():
    with patch("space.os.spawn.get_agent") as mock:
        mock.return_value = MagicMock(agent_id="agent-123", identity="test-agent")
        yield mock


@pytest.fixture
def mock_get_channel():
    with patch("space.os.bridge.api.channels.get_channel") as mock:
        mock.return_value = MagicMock(channel_id="ch-1")
        yield mock


def test_send_message_inserts_record(mock_db, mock_get_agent):
    bridge.send_message("ch-1", "sender", "hello")

    calls = mock_db.execute.call_args_list

    insert_call = next((call for call in calls if "INSERT INTO messages" in call.args[0]), None)
    assert insert_call, "message insert not executed"
    _, params = insert_call.args
    assert params[1] == "ch-1"
    assert params[2] == "agent-123"
    assert params[3] == "hello"

    update_call = next(
        (call for call in calls if "UPDATE agents SET last_active_at" in call.args[0]), None
    )
    assert update_call, "agent touch update not executed"
    _, params = update_call.args
    assert params[1] == "agent-123"


def test_send_message_returns_agent_id(mock_db, mock_get_agent):
    result = bridge.send_message("ch-1", "sender", "msg")

    assert result == "agent-123"


def test_send_message_requires_identity(mock_db):
    with pytest.raises(ValueError, match="identity is required"):
        bridge.send_message("ch-1", "", "msg")


def test_send_message_requires_channel_id(mock_db, mock_get_agent):
    with pytest.raises(ValueError, match="channel_id is required"):
        bridge.send_message("", "sender", "msg")


def test_get_messages_fetches_all(mock_db, mock_get_channel):
    mock_row = make_mock_row(
        {
            "message_id": "m-1",
            "channel_id": "ch-1",
            "agent_id": "a-1",
            "content": "hello",
            "created_at": "2024-01-01T00:00:00",
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]
    mock_db.execute.return_value.fetchone.return_value = None

    result = bridge.get_messages("ch-1")

    assert len(result) == 1


def test_get_messages_missing_channel_raises(mock_db, mock_get_channel):
    mock_get_channel.return_value = None

    with pytest.raises(ValueError, match="not found"):
        bridge.get_messages("missing")


def test_recv_messages_returns_new(mock_db, mock_get_channel, mock_get_agent):
    mock_row = make_mock_row(
        {
            "message_id": "m-1",
            "channel_id": "ch-1",
            "agent_id": "a-1",
            "content": "msg",
            "created_at": "2024-01-01T00:00:00",
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]
    mock_db.execute.return_value.fetchone.return_value = None

    messages, count, _, _ = bridge.recv_messages("ch-1", "a-2")

    assert len(messages) == 1
    assert count == 1


def test_recv_messages_count_zero_when_none(mock_db, mock_get_channel, mock_get_agent):
    mock_db.execute.return_value.fetchall.return_value = []
    mock_db.execute.return_value.fetchone.return_value = None

    messages, count, _, _ = bridge.recv_messages("ch-1", "a-1")

    assert count == 0

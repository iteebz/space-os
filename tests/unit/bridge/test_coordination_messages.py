import os
from unittest.mock import patch

import pytest

from space.bridge.coordination import messages
from space.bridge.models import Message


@pytest.fixture
def mock_storage():
    """Mock the storage module."""
    with patch("space.bridge.coordination.messages.storage") as mock_storage:
        yield mock_storage


@pytest.fixture
def mock_os_environ():
    """Mock os.environ."""
    with patch.dict(os.environ, {}, clear=True) as mock_env:
        yield mock_env


def test_send_message_passes_constitution_hash(mock_storage, mock_os_environ):
    """Verify send_message retrieves constitution_hash from env and passes it to storage.create_message."""
    mock_os_environ["AGENT_CONSTITUTION_HASH"] = "env_constitution_hash_123"
    mock_storage.get_channel_name.return_value = "mock_topic"

    messages.send_message(
        channel_id="test_channel", sender="test_sender", content="test_content", priority="high"
    )

    mock_storage.create_message.assert_called_once()
    call_kwargs = mock_storage.create_message.call_args[1]

    assert call_kwargs["channel_id"] == "test_channel"
    assert call_kwargs["sender"] == "test_sender"
    assert call_kwargs["content"] == "test_content"
    assert call_kwargs["priority"] == "high"
    assert call_kwargs["constitution_hash"] == "env_constitution_hash_123"
    assert "prompt_hash" in call_kwargs  # Ensure prompt_hash is still calculated


def test_send_message_handles_missing_constitution_hash(mock_storage, mock_os_environ):
    """Verify send_message handles missing AGENT_CONSTITUTION_HASH gracefully."""
    # AGENT_CONSTITUTION_HASH is not set in mock_os_environ
    mock_storage.get_channel_name.return_value = "mock_topic"

    messages.send_message(
        channel_id="test_channel", sender="test_sender", content="test_content", priority="high"
    )

    mock_storage.create_message.assert_called_once()
    call_kwargs = mock_storage.create_message.call_args[1]
    assert call_kwargs["constitution_hash"] is None


def test_recv_updates_passes_constitution_hash(mock_storage, mock_os_environ):
    """Verify recv_updates retrieves constitution_hash from env and passes it to storage.set_bookmark."""
    mock_os_environ["AGENT_CONSTITUTION_HASH"] = "env_constitution_hash_456"
    mock_storage.get_new_messages.return_value = (
        [Message(id=1, channel_id="c1", sender="s1", content="msg", created_at="now")],
        1,
    )
    mock_storage.get_context.return_value = "context"
    mock_storage.get_participants.return_value = ["p1"]

    messages.recv_updates(channel_id="test_channel", agent_id="test_agent")

    mock_storage.set_bookmark.assert_called_once()
    call_args = mock_storage.set_bookmark.call_args[0]

    assert call_args[0] == "test_agent"
    assert call_args[1] == "test_channel"
    assert call_args[2] == 1
    assert call_args[3] == "env_constitution_hash_456"


def test_recv_updates_handles_missing_constitution_hash(mock_storage, mock_os_environ):
    """Verify recv_updates handles missing AGENT_CONSTITUTION_HASH gracefully."""
    # AGENT_CONSTITUTION_HASH is not set in mock_os_environ
    mock_storage.get_new_messages.return_value = (
        [Message(id=1, channel_id="c1", sender="s1", content="msg", created_at="now")],
        1,
    )
    mock_storage.get_context.return_value = "context"
    mock_storage.get_participants.return_value = ["p1"]

    messages.recv_updates(channel_id="test_channel", agent_id="test_agent")

    mock_storage.set_bookmark.assert_called_once()
    call_args = mock_storage.set_bookmark.call_args[0]
    assert call_args[3] is None

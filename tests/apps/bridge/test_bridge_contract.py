import pytest
from unittest.mock import patch
from pathlib import Path

from space.apps import bridge
from space.apps.bridge import repository

@pytest.fixture
def clean_db(tmp_path):
    """
    Provides a clean database for each test.
    """
    db_path = tmp_path / "bridge.db"
    original_db_path = repository.DB_PATH
    repository.DB_PATH = db_path
    yield
    repository.DB_PATH = original_db_path

def test_create_and_get_channel(clean_db):
    channel_name = "test-channel"
    guide_hash = "test-guide-hash"

    created_channel_id = bridge.create_channel(channel_name, guide_hash)
    retrieved_channel_id = bridge.get_channel_id(channel_name)

    assert created_channel_id == retrieved_channel_id

def test_create_and_get_message(clean_db):
    channel_name = "message-channel"
    guide_hash = "message-guide-hash"
    channel_id = bridge.create_channel(channel_name, guide_hash)

    sender = "test-sender"
    content = "Hello, world!"
    prompt_hash = "test-prompt-hash"

    message_id = bridge.create_message(channel_id, sender, content, prompt_hash)
    messages = bridge.get_messages_for_channel(channel_id)

    assert len(messages) == 1
    message = messages[0]

    assert message.id == message_id
    assert message.channel_id == channel_id
    assert message.sender == sender
    assert message.content == content
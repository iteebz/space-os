import pytest
from pathlib import Path
import shutil

# This test is written against the NEW, refactored architecture.
# We will create a BridgeRepo that encapsulates all DB logic.
from space.apps.bridge.repo import BridgeRepo

@pytest.fixture
def bridge_repo(tmp_path):
    """Provides a clean BridgeRepo instance with a temporary database."""
    temp_db_path = tmp_path / "bridge.db"
    
    # In the new architecture, the repo is self-contained and takes an optional path.
    repo = BridgeRepo(db_path=temp_db_path)
    return repo

def test_create_and_get_channel(bridge_repo):
    """Defines the contract for creating and retrieving a channel."""
    channel_name = "test-channel"
    guide_hash = "test-guide-hash"

    # 1. Create the channel
    created_channel_id = bridge_repo.create_channel(channel_name, guide_hash)
    assert isinstance(created_channel_id, str)

    # 2. Retrieve the channel by name
    retrieved_channel_id = bridge_repo.get_channel_id(channel_name)
    assert created_channel_id == retrieved_channel_id

    # 3. Retrieve the channel name by ID
    retrieved_channel_name = bridge_repo.get_channel_name(retrieved_channel_id)
    assert channel_name == retrieved_channel_name

def test_create_and_get_message(bridge_repo):
    """Defines the contract for creating and retrieving a message."""
    channel_name = "message-channel"
    guide_hash = "message-guide-hash"
    channel_id = bridge_repo.create_channel(channel_name, guide_hash)

    sender = "test-sender"
    content = "Hello, world!"
    prompt_hash = "test-prompt-hash"

    # 1. Create a message
    message_id = bridge_repo.create_message(channel_id, sender, content, prompt_hash)
    assert isinstance(message_id, int)

    # 2. Retrieve messages for the channel
    messages = bridge_repo.get_messages_for_channel(channel_id)
    assert len(messages) == 1
    message = messages[0]

    assert message.id == message_id
    assert message.channel_id == channel_id
    assert message.sender == sender
    assert message.content == content

def test_fetch_sender_history(bridge_repo):
    """Defines the contract for fetching a sender's message history."""
    channel_id_1 = bridge_repo.create_channel("history-channel-1", "hash")
    channel_id_2 = bridge_repo.create_channel("history-channel-2", "hash")
    sender_1 = "sender-1"
    sender_2 = "sender-2"

    bridge_repo.create_message(channel_id_1, sender_1, "s1-msg-1", "h1")
    bridge_repo.create_message(channel_id_2, sender_1, "s1-msg-2", "h2")
    bridge_repo.create_message(channel_id_1, sender_2, "s2-msg-1", "h3")

    # 1. Fetch history for sender_1
    history = bridge_repo.fetch_sender_history(sender_1)
    assert len(history) == 2
    assert history[0].content == "s1-msg-1"
    assert history[1].content == "s1-msg-2"

    # 2. Fetch history for sender_2
    history_2 = bridge_repo.fetch_sender_history(sender_2)
    assert len(history_2) == 1
    assert history_2[0].content == "s2-msg-1"

    # 3. Fetch history for a sender with no messages
    history_none = bridge_repo.fetch_sender_history("sender-none")
    assert len(history_none) == 0

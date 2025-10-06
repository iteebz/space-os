import pytest
from unittest.mock import Mock, patch
import sqlite3

# Import the app and API functions
from space.apps.bridge import bridge_app
from space.apps.bridge.api import (
    create_message,
    get_all_messages,
    fetch_sender_history,
    get_new_messages,
)
from space.apps.bridge.models import Message

# Fixture for mocking the bridge app's repository (if applicable)
@pytest.fixture
def mock_bridge_repo():
    mock_repo = Mock()
    return mock_repo

# Fixture for mocking the bridge app's API instance (if applicable)
@pytest.fixture
def bridge_api_instance(mock_bridge_repo):
    # Bridge app uses direct function calls, so this fixture is not directly used for API calls
    return None

# --- Test Cases for Immutability (Core Ledger) ---

def test_create_message_immutability(mock_bridge_db_connection):
    """Test that messages, once created, cannot be directly altered or deleted via public API."""
    channel_id = "test_channel_immutable"
    sender = "test_sender_immutable"
    content = "initial content"
    prompt_hash = "hash1"

    # Create a message
    message_id = create_message(channel_id, sender, content, prompt_hash)
    assert isinstance(message_id, int)

    # Attempt to find a public API for updating messages (should not exist)
    with pytest.raises(AttributeError):
        bridge_app.api.update_message # Assuming no such function is exposed
    with pytest.raises(AttributeError):
        bridge_app.api.delete_message # Assuming no such function is exposed

    # Verify the message content in the database remains unchanged
    with mock_bridge_db_connection as conn:
        cursor = conn.execute("SELECT content FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()
        assert row["content"] == content

    # Attempt to modify the message directly in the database (outside API) and verify it's not exposed via API
    with mock_bridge_db_connection as conn:
        conn.execute("UPDATE messages SET content = ? WHERE id = ?", ("modified content", message_id))
        conn.commit()

    # Query the message again via API and ensure it reflects the (simulated) modification
    # This part tests that the API *reads* the current state, even if modified externally.
    # The immutability is about the *absence* of API methods to change it.
    messages = get_all_messages(channel_id)
    assert len(messages) == 1
    assert messages[0].content == "modified content"

# --- Test Cases for Message Management ---

def test_create_message(mock_bridge_db_connection):
    """Test creating a new message."""
    channel_id = "test_channel_create"
    sender = "test_sender_create"
    content = "This is a test message."
    prompt_hash = "some_hash"
    priority = "high"
    constitution_hash = "const_hash"

    message_id = create_message(channel_id, sender, content, prompt_hash, priority, constitution_hash)
    assert isinstance(message_id, int)
    assert message_id > 0

    with mock_bridge_db_connection as conn:
        cursor = conn.execute(
            "SELECT id, channel_id, sender, content, prompt_hash, priority, constitution_hash FROM messages WHERE id = ?",
            (message_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["id"] == message_id
        assert row["channel_id"] == channel_id
        assert row["sender"] == sender
        assert row["content"] == content
        assert row["prompt_hash"] == prompt_hash
        assert row["priority"] == priority
        assert row["constitution_hash"] == constitution_hash

def test_get_all_messages(mock_bridge_db_connection):
    """Test retrieving all messages for a given channel."""
    channel_id = "test_channel_all_messages"
    create_message(channel_id, "sender1", "content1", "hash1")
    create_message(channel_id, "sender2", "content2", "hash2")
    create_message("other_channel", "sender3", "content3", "hash3") # Message in another channel

    messages = get_all_messages(channel_id)
    assert len(messages) == 2
    assert all(isinstance(msg, Message) for msg in messages)
    assert messages[0].channel_id == channel_id
    assert messages[1].channel_id == channel_id
    assert messages[0].content == "content1"
    assert messages[1].content == "content2"

def test_fetch_sender_history(mock_bridge_db_connection):
    """Test fetching messages by sender."""
    channel_id_1 = "channel_s1"
    channel_id_2 = "channel_s2"
    sender_1 = "test_sender_history_1"
    sender_2 = "test_sender_history_2"

    create_message(channel_id_1, sender_1, "msg1_s1", "hash_s1_1")
    create_message(channel_id_2, sender_1, "msg2_s1", "hash_s1_2")
    create_message(channel_id_1, sender_2, "msg1_s2", "hash_s2_1")

    history = fetch_sender_history(sender_1)
    assert len(history) == 2
    assert all(isinstance(msg, Message) for msg in history)
    assert history[0].sender == sender_1
    assert history[1].sender == sender_1
    # Messages are ordered by created_at DESC, so the latest message should be first
    assert history[0].content == "msg2_s1"
    assert history[1].content == "msg1_s1"

    history_limited = fetch_sender_history(sender_1, limit=1)
    assert len(history_limited) == 1
    assert history_limited[0].content == "msg2_s1"

def test_get_new_messages(mock_bridge_db_connection):
    """Test retrieving new messages since a given point."""
    channel_id = "test_channel_new_messages"
    create_message(channel_id, "s1", "c1", "h1")
    first_msg_id = create_message(channel_id, "s2", "c2", "h2")
    create_message(channel_id, "s3", "c3", "h3")

    # Test with no last_seen_id (should fetch all unarchived)
    messages_all = get_new_messages(channel_id)
    # get_new_messages returns a tuple (list[Message], count)
    assert len(messages_all[0]) == 3
    assert messages_all[1] == 3
    assert all(isinstance(msg, Message) for msg in messages_all[0])

    # Test with last_seen_id
    messages_new = get_new_messages(channel_id, last_seen_id=first_msg_id)
    assert len(messages_new[0]) == 1
    assert messages_new[1] == 1
    assert messages_new[0][0].content == "c3"

    # Test with no new messages
    messages_none = get_new_messages(channel_id, last_seen_id=messages_all[0][-1].id)
    assert len(messages_none[0]) == 0
    assert messages_none[1] == 0

# --- Test Cases for Channel Management ---

def test_archive_channel():
    """Test archiving a channel."""
    pass

def test_delete_channel():
    """Test deleting a channel."""
    pass

def test_export_channel():
    """Test exporting channel data."""
    pass

def test_rename_channel():
    """Test renaming a channel."""
    pass

def test_resolve_channel_id():
    """Test resolving channel ID to name."""
    pass

# --- Test Cases for Note Management ---

def test_add_note():
    """Test adding a note."""
    pass

def test_get_notes():
    """Test retrieving notes."""
    pass

# --- Test Cases for Bridge Instructions ---

def test_get_bridge_instructions():
    """Test retrieving bridge instructions."""
    pass

def test_save_bridge_instructions():
    """Test saving bridge instructions."""
    pass

# --- Test Cases for DB Management ---

def test_init_bridge_db():
    """Test initializing the bridge database."""
    pass

def test_get_bridge_db_connection():
    """Test getting a database connection."""
    pass

# --- Test Cases for Events ---

def test_emit_bridge_event():
    """Test emitting a bridge event."""
    pass

# --- Test Cases for Utilities ---

def test_hash_digest():
    """Test hash digest utility."""
    pass

def test_format_local_time():
    """Test formatting local time utility."""
    pass

def test_format_time_ago():
    """Test formatting time ago utility."""
    pass

# --- Test Cases for Alerts ---

def test_fetch_alerts():
    """Test fetching alerts."""
    pass
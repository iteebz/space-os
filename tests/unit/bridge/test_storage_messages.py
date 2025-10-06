import sqlite3
from unittest.mock import patch

import pytest

from space.apps.bridge.storage import db as bridge_db  # Import db to access init_db
from space.apps.bridge.storage import messages


@pytest.fixture
def in_memory_bridge_db():
    """Fixture for a persistent in-memory SQLite bridge database."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Patch get_db_connection to return this persistent connection
    with patch("space.bridge.storage.db.get_db_connection", return_value=conn):
        bridge_db.init_db()  # Initialize the bridge db schema on this connection
        yield conn
        conn.close()


def test_create_message_stores_constitution_hash(in_memory_bridge_db):
    """Verify that create_message correctly stores constitution_hash."""
    channel_id = "test_channel_1"
    sender = "test_sender_1"
    content = "test_content_1"
    prompt_hash = "test_prompt_hash_1"
    priority = "normal"
    constitution_hash = "test_constitution_hash_1"

    message_id = messages.create_message(
        channel_id=channel_id,
        sender=sender,
        content=content,
        prompt_hash=prompt_hash,
        priority=priority,
        constitution_hash=constitution_hash,
    )

    with bridge_db.get_db_connection() as conn:
        cursor = conn.execute("SELECT constitution_hash FROM messages WHERE id = ?", (message_id,))
        retrieved_hash = cursor.fetchone()[0]
        assert retrieved_hash == constitution_hash


def test_get_all_messages_retrieves_constitution_hash(in_memory_bridge_db):
    """Verify that get_all_messages retrieves constitution_hash."""
    channel_id = "test_channel_2"
    sender = "test_sender_2"
    content = "test_content_2"
    prompt_hash = "test_prompt_hash_2"
    priority = "normal"
    constitution_hash = "test_constitution_hash_2"

    messages.create_message(
        channel_id=channel_id,
        sender=sender,
        content=content,
        prompt_hash=prompt_hash,
        priority=priority,
        constitution_hash=constitution_hash,
    )

    all_msgs = messages.get_all_messages(channel_id)
    assert len(all_msgs) == 1
    assert all_msgs[0].constitution_hash == constitution_hash


def test_create_message_with_none_constitution_hash(in_memory_bridge_db):
    """Verify create_message handles None constitution_hash."""
    channel_id = "test_channel_3"
    sender = "test_sender_3"
    content = "test_content_3"
    prompt_hash = "test_prompt_hash_3"
    priority = "normal"
    constitution_hash = None

    message_id = messages.create_message(
        channel_id=channel_id,
        sender=sender,
        content=content,
        prompt_hash=prompt_hash,
        priority=priority,
        constitution_hash=constitution_hash,
    )

    with bridge_db.get_db_connection() as conn:
        cursor = conn.execute("SELECT constitution_hash FROM messages WHERE id = ?", (message_id,))
        retrieved_hash = cursor.fetchone()[0]
        assert retrieved_hash is None

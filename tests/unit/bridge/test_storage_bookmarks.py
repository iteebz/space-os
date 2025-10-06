import sqlite3
from unittest.mock import patch

import pytest

from space.bridge.storage import bookmarks
from space.bridge.storage import db as bridge_db  # Import db to access init_db


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


def test_set_bookmark_stores_constitution_hash(in_memory_bridge_db):
    """Verify that set_bookmark correctly stores constitution_hash."""
    agent_id = "test_agent_1"
    channel_id = "test_channel_1"
    last_seen_id = 10
    constitution_hash = "test_constitution_hash_1"

    bookmarks.set_bookmark(
        agent_id=agent_id,
        channel_id=channel_id,
        last_seen_id=last_seen_id,
        constitution_hash=constitution_hash,
    )

    with bridge_db.get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT constitution_hash FROM bookmarks WHERE agent_id = ? AND channel_id = ?",
            (agent_id, channel_id),
        )
        retrieved_hash = cursor.fetchone()[0]
        assert retrieved_hash == constitution_hash


def test_set_bookmark_with_none_constitution_hash(in_memory_bridge_db):
    """Verify set_bookmark handles None constitution_hash."""
    agent_id = "test_agent_2"
    channel_id = "test_channel_2"
    last_seen_id = 20
    constitution_hash = None

    bookmarks.set_bookmark(
        agent_id=agent_id,
        channel_id=channel_id,
        last_seen_id=last_seen_id,
        constitution_hash=constitution_hash,
    )

    with bridge_db.get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT constitution_hash FROM bookmarks WHERE agent_id = ? AND channel_id = ?",
            (agent_id, channel_id),
        )
        retrieved_hash = cursor.fetchone()[0]
        assert retrieved_hash is None

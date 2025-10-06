import pytest
from space.apps.bridge import channels
import sqlite3

def test_create_channel(in_memory_db):
    """
    Tests that a channel can be created successfully.
    """
    channel_name = "test_channel"
    guide_hash = "test_hash"

    channel_id = channels.create(channel_name, guide_hash)

    assert channel_id is not None
    assert isinstance(channel_id, str)

    # Verify it's in the database
    cursor = in_memory_db.execute("SELECT id, name, guide_hash FROM channels WHERE id = ?", (channel_id,))
    result = cursor.fetchone()

    assert result is not None
    assert result["id"] == channel_id
    assert result["name"] == channel_name
    assert result["guide_hash"] == guide_hash

def test_create_channel_duplicate_name_fails(in_memory_db):
    """
    Tests that creating a channel with a duplicate name raises an error.
    """
    channel_name = "duplicate_channel"
    guide_hash = "hash1"
    channels.create(channel_name, guide_hash)

    with pytest.raises(sqlite3.IntegrityError):
        channels.create(channel_name, "hash2")

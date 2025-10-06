import pytest
from unittest.mock import Mock, patch
import sqlite3
from pathlib import Path
from datetime import datetime
import time

from space.apps.memory.repo import MemoryRepo
from space.apps.memory.models import Memory
from space.os.core.storage import Repo

# Mock the uuid7.uuid7 function to return predictable UUIDs
@pytest.fixture(autouse=True)
def mock_uuid7():
    with patch('space.os.lib.uuid7.uuid7') as mock_uuid:
        mock_uuid.side_effect = [f"test-uuid-{i}" for i in range(100)]
        yield mock_uuid

@pytest.fixture
def in_memory_repo():
    # Create an in-memory SQLite database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row # Enable dictionary-like access to rows

    # Manually apply the schema for testing
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            uuid TEXT PRIMARY KEY,
            identity TEXT NOT NULL,
            topic TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
    """)
    conn.commit()

    repo = MemoryRepo(app_name="test_memory")

    # Mock the _connect method to return our in-memory connection
    repo._connect = Mock(return_value=conn)

    yield repo, conn # Yield both repo and conn

    conn.close()

def test_add_memory_entry(in_memory_repo):
    repo, conn = in_memory_repo
    entry_uuid = repo.add("user1", "topicA", "message1")
    assert entry_uuid == "test-uuid-0"

    cursor = conn.execute("SELECT * FROM memory WHERE uuid = ?", (entry_uuid,))
    row = cursor.fetchone()
    assert row is not None
    assert row["identity"] == "user1"
    assert row["topic"] == "topicA"
    assert row["message"] == "message1"

def test_get_memory_entries(in_memory_repo):
    repo, conn = in_memory_repo
    repo.add("user1", "topicA", "message1", created_at=1)
    repo.add("user1", "topicA", "message2", created_at=2)
    repo.add("user2", "topicB", "message3")

    entries = repo.get("user1", "topicA")
    assert len(entries) == 2
    assert entries[0].message == "message2" # Ordered by created_at DESC
    assert entries[1].message == "message1"

    entries = repo.get("user1")
    assert len(entries) == 2

    entries = repo.get("user2", "topicB")
    assert len(entries) == 1
    assert entries[0].message == "message3"

def test_update_memory_entry(in_memory_repo):
    repo, conn = in_memory_repo
    entry_uuid = repo.add("user1", "topicA", "message1")
    repo.update(entry_uuid, "updated_message")

    entries = repo.get("user1", "topicA")
    assert len(entries) == 1
    assert entries[0].message == "updated_message"

def test_delete_memory_entry(in_memory_repo):
    repo, conn = in_memory_repo
    entry_uuid = repo.add("user1", "topicA", "message1")
    repo.delete(entry_uuid)

    entries = repo.get("user1", "topicA")
    assert len(entries) == 0

def test_clear_memory_entries(in_memory_repo):
    repo, conn = in_memory_repo
    repo.add("user1", "topicA", "message1")
    repo.add("user1", "topicA", "message2")
    repo.add("user2", "topicB", "message3")

    repo.clear("user1", "topicA")
    assert len(repo.get("user1", "topicA")) == 0
    assert len(repo.get("user2", "topicB")) == 1

    repo.clear("user2")
    assert len(repo.get("user2", "topicB")) == 0

def test_resolve_uuid_unique(in_memory_repo):
    repo, conn = in_memory_repo
    full_uuid = repo.add("user1", "topicA", "message1")
    resolved_uuid = repo._resolve_uuid(full_uuid[-8:])
    assert resolved_uuid == full_uuid

def test_resolve_uuid_not_found(in_memory_repo):
    repo, conn = in_memory_repo
    with pytest.raises(ValueError, match="No entry found with UUID ending in 'non-existent'"):
        repo._resolve_uuid("non-existent")

def test_resolve_uuid_ambiguous(in_memory_repo):
    repo, conn = in_memory_repo
    repo.add("user1", "topicA", "message1") # test-uuid-0
    repo.add("user1", "topicA", "message2") # test-uuid-1

    # Manually insert an entry to create ambiguity for "uuid-0"
    conn.execute("INSERT INTO memory (uuid, identity, topic, message, created_at) VALUES (?, ?, ?, ?, ?)",
                 ("another-test-uuid-0", "user3", "topicC", "message4", int(datetime.now().timestamp())))
    conn.commit()

    with pytest.raises(ValueError, match="Ambiguous UUID: 'uuid-0' matches multiple entries:"):
        repo._resolve_uuid("uuid-0")

def test_row_to_entity(in_memory_repo):
    repo, conn = in_memory_repo
    # Mock a sqlite3.Row object
    mock_row_data = {
        "uuid": "test-uuid-mock",
        "identity": "mock_user",
        "topic": "mock_topic",
        "message": "mock_message",
        "created_at": 1678886400 # Example timestamp
    }
    mock_row = Mock()
    mock_row.__getitem__ = lambda s, key: mock_row_data[key] # Corrected lambda

    memory_obj = repo._row_to_entity(mock_row)
    assert isinstance(memory_obj, Memory)
    assert memory_obj.uuid == "test-uuid-mock"
    assert memory_obj.identity == "mock_user"
    assert memory_obj.topic == "mock_topic"
    assert memory_obj.message == "mock_message"
    assert memory_obj.created_at == 1678886400

import pytest
from unittest.mock import patch
from pathlib import Path
from datetime import datetime

# Import the public API of the memory app
from space.apps import memory
from space.apps.memory import repository

@pytest.fixture
def clean_db(tmp_path):
    """
    Provides a clean database for each test and patches the repository.
    """
    db_path = tmp_path / "memory.db"
    
    original_db_path = repository.DB_PATH
    repository.DB_PATH = db_path
    yield
    repository.DB_PATH = original_db_path

@patch('space.os.lib.uuid7.uuid7') # Patch the actual uuid7 function being called
def test_add_and_get_memories(mock_uuid7, clean_db):
    # Mock datetime to control created_at for deterministic ordering
    with patch('space.apps.memory.repository.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 1, 10, 0, 0)
        mock_uuid7.return_value = "test-uuid-1"
        
        # Add a memory
        memory.add_memory("test_identity", "test_topic", "test_message")

        mock_datetime.now.return_value = datetime(2025, 1, 1, 10, 0, 1)
        mock_uuid7.return_value = "test-uuid-2"
        memory.add_memory("test_identity_2", "test_topic_2", "test_message_2")

        # Get all memories
        memories = memory.get_all_memories()
    
        assert len(memories) == 2
        assert memories[0].uuid == "test-uuid-2" # Most recent first
        assert memories[1].uuid == "test-uuid-1"

        assert memories[0].identity == "test_identity_2"
        assert memories[0].topic == "test_topic_2"
        assert memories[0].message == "test_message_2"

        assert memories[1].identity == "test_identity"
        assert memories[1].topic == "test_topic"
        assert memories[1].message == "test_message"

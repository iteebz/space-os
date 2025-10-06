import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from space.apps.memory.api import MemoryApi # Import MemoryApi class
from space.apps.memory.models import Memory
from space.apps.memory.app import memory_app

@pytest.fixture
def mock_memory_repository():
    """
    Fixture to mock the MemoryRepository instance.
    """
    mock_repo = Mock()
    return mock_repo

@pytest.fixture
def memory_api_instance(mock_memory_repository):
    """
    Fixture to provide an instance of MemoryApi with a mocked repository.
    """
    return MemoryApi(mock_memory_repository)

def test_add_memory_entry(memory_api_instance, mock_memory_repository):
    identity = "test_agent"
    topic = "test_topic"
    message = "This is a test message."

    memory_api_instance.add_memory_entry(identity, topic, message)

    mock_memory_repository.add.assert_called_once_with(identity, topic, message)

def test_get_memory_entries(memory_api_instance, mock_memory_repository):
    identity = "test_agent"
    topic = "test_topic"
    current_timestamp = int(datetime.now().timestamp())
    mock_entries = [
        Memory(uuid=uuid4(), identity=identity, topic=topic, message="msg1", created_at=current_timestamp),
        Memory(uuid=uuid4(), identity=identity, topic=topic, message="msg2", created_at=current_timestamp),
    ]
    mock_memory_repository.get.return_value = mock_entries

    entries = memory_api_instance.get_memory_entries(identity, topic)

    mock_memory_repository.get.assert_called_once_with(identity, topic)
    assert entries == mock_entries

def test_get_memory_entries_by_identity_only(memory_api_instance, mock_memory_repository):
    identity = "test_agent"
    current_timestamp = int(datetime.now().timestamp())
    mock_entries = [
        Memory(uuid=uuid4(), identity=identity, topic="t1", message="msg1", created_at=current_timestamp),
        Memory(uuid=uuid4(), identity=identity, topic="t2", message="msg2", created_at=current_timestamp),
    ]
    mock_memory_repository.get.return_value = mock_entries

    entries = memory_api_instance.get_memory_entries(identity)

    mock_memory_repository.get.assert_called_once_with(identity, None)
    assert entries == mock_entries

def test_edit_memory_entry(memory_api_instance, mock_memory_repository):
    entry_uuid = str(uuid4())
    new_message = "Updated message."

    memory_api_instance.edit_memory_entry(entry_uuid, new_message)

    mock_memory_repository.update.assert_called_once_with(entry_uuid, new_message)

def test_edit_non_existent_entry_raises_error(memory_api_instance, mock_memory_repository):
    entry_uuid = str(uuid4())
    new_message = "Updated message."
    mock_memory_repository.update.side_effect = ValueError(f"No entry found with UUID: {entry_uuid}")

    with pytest.raises(ValueError, match=f"No entry found with UUID: {entry_uuid}"):
        memory_api_instance.edit_memory_entry(entry_uuid, new_message)
    mock_memory_repository.update.assert_called_once_with(entry_uuid, new_message)

def test_delete_memory_entry(memory_api_instance, mock_memory_repository):
    entry_uuid = str(uuid4())

    memory_api_instance.delete_memory_entry(entry_uuid)

    mock_memory_repository.delete.assert_called_once_with(entry_uuid)

def test_delete_non_existent_entry_raises_error(memory_api_instance, mock_memory_repository):
    entry_uuid = str(uuid4())
    mock_memory_repository.delete.side_effect = ValueError(f"No entry found with UUID: {entry_uuid}")

    with pytest.raises(ValueError, match=f"No entry found with UUID: {entry_uuid}"):
        memory_api_instance.delete_memory_entry(entry_uuid)
    mock_memory_repository.delete.assert_called_once_with(entry_uuid)

def test_clear_memory_entries_by_topic(memory_api_instance, mock_memory_repository):
    identity = "test_agent"
    topic = "test_topic"

    memory_api_instance.clear_memory_entries(identity, topic)

    mock_memory_repository.clear.assert_called_once_with(identity, topic)

def test_clear_all_memory_entries_for_identity(memory_api_instance, mock_memory_repository):
    identity = "test_agent"

    memory_api_instance.clear_memory_entries(identity)

    mock_memory_repository.clear.assert_called_once_with(identity, None)
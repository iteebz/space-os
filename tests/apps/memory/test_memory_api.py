import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from space.apps.memory.api import (
    add_memory_entry,
    get_memory_entries,
    edit_memory_entry,
    delete_memory_entry,
    clear_memory_entries,
)
from space.apps.memory.models import Memory
from space.apps.memory.app import memory_app

@pytest.fixture
def mock_memory_repository():
    """
    Fixture to mock the MemoryRepository instance used by the API.
    """
    mock_repo = Mock()
    with patch.dict(memory_app.repositories, {"memory": mock_repo}):
        yield mock_repo

def test_add_memory_entry(mock_memory_repository):
    identity = "test_agent"
    topic = "test_topic"
    message = "This is a test message."

    add_memory_entry(identity, topic, message)

    mock_memory_repository.add.assert_called_once_with(identity, topic, message)

def test_get_memory_entries(mock_memory_repository):
    identity = "test_agent"
    topic = "test_topic"
    current_timestamp = int(datetime.now().timestamp())
    mock_entries = [
        Memory(uuid=uuid4(), identity=identity, topic=topic, message="msg1", created_at=current_timestamp),
        Memory(uuid=uuid4(), identity=identity, topic=topic, message="msg2", created_at=current_timestamp),
    ]
    mock_memory_repository.get.return_value = mock_entries

    entries = get_memory_entries(identity, topic)

    mock_memory_repository.get.assert_called_once_with(identity, topic)
    assert entries == mock_entries

def test_get_memory_entries_by_identity_only(mock_memory_repository):
    identity = "test_agent"
    current_timestamp = int(datetime.now().timestamp())
    mock_entries = [
        Memory(uuid=uuid4(), identity=identity, topic="t1", message="msg1", created_at=current_timestamp),
        Memory(uuid=uuid4(), identity=identity, topic="t2", message="msg2", created_at=current_timestamp),
    ]
    mock_memory_repository.get.return_value = mock_entries

    entries = get_memory_entries(identity)

    mock_memory_repository.get.assert_called_once_with(identity, None)
    assert entries == mock_entries

def test_edit_memory_entry(mock_memory_repository):
    entry_uuid = str(uuid4())
    new_message = "Updated message."

    edit_memory_entry(entry_uuid, new_message)

    mock_memory_repository.update.assert_called_once_with(entry_uuid, new_message)

def test_edit_non_existent_entry_raises_error(mock_memory_repository):
    entry_uuid = str(uuid4())
    new_message = "Updated message."
    mock_memory_repository.update.side_effect = ValueError(f"No entry found with UUID: {entry_uuid}")

    with pytest.raises(ValueError, match=f"No entry found with UUID: {entry_uuid}"):
        edit_memory_entry(entry_uuid, new_message)
    mock_memory_repository.update.assert_called_once_with(entry_uuid, new_message)

def test_delete_memory_entry(mock_memory_repository):
    entry_uuid = str(uuid4())

    delete_memory_entry(entry_uuid)

    mock_memory_repository.delete.assert_called_once_with(entry_uuid)

def test_delete_non_existent_entry_raises_error(mock_memory_repository):
    entry_uuid = str(uuid4())
    mock_memory_repository.delete.side_effect = ValueError(f"No entry found with UUID: {entry_uuid}")

    with pytest.raises(ValueError, match=f"No entry found with UUID: {entry_uuid}"):
        delete_memory_entry(entry_uuid)
    mock_memory_repository.delete.assert_called_once_with(entry_uuid)

def test_clear_memory_entries_by_topic(mock_memory_repository):
    identity = "test_agent"
    topic = "test_topic"

    clear_memory_entries(identity, topic)

    mock_memory_repository.clear.assert_called_once_with(identity, topic)

def test_clear_all_memory_entries_for_identity(mock_memory_repository):
    identity = "test_agent"

    clear_memory_entries(identity)

    mock_memory_repository.clear.assert_called_once_with(identity, None)

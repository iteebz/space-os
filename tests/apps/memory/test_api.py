import pytest
from unittest.mock import Mock, patch
from space.apps.memory import api
from space.apps.memory.models import Memory

@pytest.fixture
def mock_memory_repo():
    return Mock()

@pytest.fixture
def mock_app_instance(mock_memory_repo):
    mock_app = Mock()
    mock_app.repositories = {'memory': mock_memory_repo}
    return mock_app

@pytest.fixture(autouse=True)
def setup_api_instance(mock_memory_repo):
    api._set_memory_repo_instance(mock_memory_repo)
    yield
    api._set_memory_repo_instance(None) # Clean up global state after test

def test_add_memory_entry(mock_memory_repo):
    mock_memory_repo.add.return_value = "test-uuid"
    with patch('space.apps.memory.api.track') as mock_track:
        api.add_memory_entry("test_identity", "test_topic", "test_message")
        mock_memory_repo.add.assert_called_once_with("test_identity", "test_topic", "test_message")
        mock_track.assert_called_once_with(
            source="memory",
            event_type="entry.add",
            identity="test_identity",
            data={"topic": "test_topic", "message": "test_message", "uuid": "test-uuid"}
        )

def test_get_memory_entries(mock_memory_repo):
    mock_memory_repo.get.return_value = [
        Memory(uuid="1", identity="id1", topic="t1", message="m1", created_at=123),
        Memory(uuid="2", identity="id1", topic="t1", message="m2", created_at=456)
    ]
    entries = api.get_memory_entries("test_identity", "test_topic")
    mock_memory_repo.get.assert_called_once_with("test_identity", "test_topic")
    assert len(entries) == 2
    assert entries[0].message == "m1"

def test_edit_memory_entry(mock_memory_repo):
    entry_uuid = "long-uuid-for-testing-slicing-short-uuid"
    with patch('space.apps.memory.api.track') as mock_track:
        api.edit_memory_entry(entry_uuid, "new_message")
        mock_memory_repo.update.assert_called_once_with(entry_uuid, "new_message")
        mock_track.assert_called_once_with(
            source="memory",
            event_type="entry.edit",
            identity=None,
            data={"uuid": entry_uuid[-8:]}
        )

def test_delete_memory_entry(mock_memory_repo):
    entry_uuid = "long-uuid-for-testing-slicing-short-uuid"
    with patch('space.apps.memory.api.track') as mock_track:
        api.delete_memory_entry(entry_uuid)
        mock_memory_repo.delete.assert_called_once_with(entry_uuid)
        mock_track.assert_called_once_with(
            source="memory",
            event_type="entry.delete",
            identity=None,
            data={"uuid": entry_uuid[-8:]}
        )

def test_clear_memory_entries(mock_memory_repo):
    api.clear_memory_entries("test_identity", "test_topic")
    mock_memory_repo.clear.assert_called_once_with("test_identity", "test_topic")

def test_api_functions_raise_error_if_not_initialized():
    api._set_memory_repo_instance(None) # Ensure it's not initialized
    with pytest.raises(RuntimeError, match="Memory repository instance not initialized in API."):
        api.add_memory_entry("test_identity", "test_topic", "test_message")
    with pytest.raises(RuntimeError, match="Memory repository instance not initialized in API."):
        api.get_memory_entries("test_identity")
    with pytest.raises(RuntimeError, match="Memory repository instance not initialized in API."):
        api.edit_memory_entry("uuid", "new_message")
    with pytest.raises(RuntimeError, match="Memory repository instance not initialized in API."):
        api.delete_memory_entry("uuid")
    with pytest.raises(RuntimeError, match="Memory repository instance not initialized in API."):
        api.clear_memory_entries("test_identity")

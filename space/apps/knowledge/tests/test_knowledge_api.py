import pytest
from unittest.mock import Mock, patch
from space.apps.knowledge.api import KnowledgeApi # Import KnowledgeApi class
from space.apps.knowledge.models import Knowledge

@pytest.fixture
def mock_knowledge_repository():
    """
    Fixture to mock the KnowledgeRepo instance.
    """
    mock_repo = Mock()
    return mock_repo

@pytest.fixture
def knowledge_api_instance(mock_knowledge_repository):
    """
    Fixture to provide an instance of KnowledgeApi with a mocked repository.
    """
    return KnowledgeApi(mock_knowledge_repository)

def test_write_and_query_knowledge(knowledge_api_instance, mock_knowledge_repository):
    """Test writing and querying a single knowledge entry."""
    mock_knowledge_repository.add.return_value = "test_entry_id"
    mock_knowledge_repository.get.return_value = [
        Knowledge(id="test_entry_id", domain="test_domain", contributor="test_contributor", content="test_content", confidence=None, created_at="2023-01-01T00:00:00Z")
    ]

    with patch('space.apps.knowledge.api.events.track') as mock_track: # Corrected patch target
        entry_id = knowledge_api_instance.write_knowledge(
            domain="test_domain",
            contributor="test_contributor",
            content="test_content",
        )
        assert isinstance(entry_id, str)
        mock_knowledge_repository.add.assert_called_once_with("test_domain", "test_contributor", "test_content", None)
        mock_track.assert_called_once_with(
            source="knowledge",
            event_type="write",
            identity="test_contributor",
            data={"id": "test_entry_id", "domain": "test_domain"},
        )

    entries = knowledge_api_instance.query_knowledge(entry_id=entry_id)
    mock_knowledge_repository.get.assert_called_once_with(None, None, entry_id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.id == entry_id
    assert entry.domain == "test_domain"
    assert entry.contributor == "test_contributor"
    assert entry.content == "test_content"

def test_query_by_domain(knowledge_api_instance, mock_knowledge_repository):
    """Test querying knowledge entries by domain."""
    mock_knowledge_repository.get.return_value = [
        Knowledge(id="id1", domain="domain1", contributor="contrib1", content="content1", confidence=None, created_at="2023-01-01T00:00:00Z"),
        Knowledge(id="id3", domain="domain1", contributor="contrib3", content="content3", confidence=None, created_at="2023-01-01T00:00:00Z"),
    ]

    entries = knowledge_api_instance.query_knowledge(domain="domain1")
    mock_knowledge_repository.get.assert_called_once_with("domain1", None, None)
    assert len(entries) == 2
    assert all(entry.domain == "domain1" for entry in entries)

def test_query_by_contributor(knowledge_api_instance, mock_knowledge_repository):
    """Test querying knowledge entries by contributor."""
    mock_knowledge_repository.get.return_value = [
        Knowledge(id="id1", domain="domain1", contributor="contrib1", content="content1", confidence=None, created_at="2023-01-01T00:00:00Z"),
        Knowledge(id="id3", domain="domain3", contributor="contrib1", content="content3", confidence=None, created_at="2023-01-01T00:00:00Z"),
    ]

    entries = knowledge_api_instance.query_knowledge(contributor="contrib1")
    mock_knowledge_repository.get.assert_called_once_with(None, "contrib1", None)
    assert len(entries) == 2
    assert all(entry.contributor == "contrib1" for entry in entries)

def test_query_all(knowledge_api_instance, mock_knowledge_repository):
    """Test querying all knowledge entries."""
    mock_knowledge_repository.get.return_value = [
        Knowledge(id="id1", domain="domain1", contributor="contrib1", content="content1", confidence=None, created_at="2023-01-01T00:00:00Z"),
        Knowledge(id="id2", domain="domain2", contributor="contrib2", content="content2", confidence=None, created_at="2023-01-01T00:00:00Z"),
    ]

    entries = knowledge_api_instance.query_knowledge()
    mock_knowledge_repository.get.assert_called_once_with(None, None, None)
    assert len(entries) == 2

def test_query_non_existent(knowledge_api_instance, mock_knowledge_repository):
    """Test querying for a non-existent entry."""
    mock_knowledge_repository.get.return_value = []

    entries = knowledge_api_instance.query_knowledge(entry_id="non_existent_id")
    mock_knowledge_repository.get.assert_called_once_with(None, None, "non_existent_id")
    assert len(entries) == 0

def test_edit_knowledge(knowledge_api_instance, mock_knowledge_repository):
    """Test editing a knowledge entry."""
    entry_id = "test_entry_id"
    new_content = "updated_content"
    new_confidence = 0.9

    with patch('space.apps.knowledge.api.events.track') as mock_track:
        knowledge_api_instance.edit_knowledge(entry_id, new_content, new_confidence)
        mock_knowledge_repository.update.assert_called_once_with(entry_id, new_content, new_confidence)
        mock_track.assert_called_once_with(
            source="knowledge",
            event_type="edit",
            data={"id": entry_id},
        )

def test_delete_knowledge(knowledge_api_instance, mock_knowledge_repository):
    """Test deleting a knowledge entry."""
    entry_id = "test_entry_id"

    with patch('space.apps.knowledge.api.events.track') as mock_track:
        knowledge_api_instance.delete_knowledge(entry_id)
        mock_knowledge_repository.delete.assert_called_once_with(entry_id)
        mock_track.assert_called_once_with(
            source="knowledge",
            event_type="delete",
            data={"id": entry_id},
        )

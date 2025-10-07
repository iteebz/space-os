import pytest
from unittest.mock import patch
from pathlib import Path

# Import the public API of the spawn app
from space.apps import spawn
from space.apps.spawn.models import Identity
from space.apps.spawn.repo import SpawnRepo

@pytest.fixture
def clean_db(tmp_path):
    """
    Provides a clean database for each test and patches the _get_repo function.
    """
    db_path = tmp_path / "spawn.db"
    
    with patch('space.apps.spawn._get_repo') as mock_get_repo:
        mock_get_repo.return_value = SpawnRepo(db_path=db_path)
        yield

@pytest.fixture
def mock_uuid7():
    """
    Mocks uuid7.uuid7() to return predictable UUIDs.
    """
    with patch('space.os.lib.uuid7.uuid7') as mock_uuid:
        mock_uuid.side_effect = [
            '00000000-0000-7000-8000-000000000001',
            '00000000-0000-7000-8000-000000000002',
            '00000000-0000-7000-8000-000000000003',
            '00000000-0000-7000-8000-000000000004',
            '00000000-0000-7000-8000-000000000005',
            '00000000-0000-7000-8000-000000000006',
        ] * 3 # Ensure enough UUIDs
        yield

@patch('space.apps.spawn.track')
def test_add_and_get_identity(mock_track, clean_db, mock_uuid7):
    identity_id = "test_agent_1"
    identity_type = "agent"

    added_identity = spawn.add_identity(identity_id, identity_type)

    assert added_identity is not None
    assert added_identity.id == identity_id
    assert added_identity.type == identity_type

    retrieved_identity = spawn.get_identity(identity_id)

    assert retrieved_identity is not None
    assert retrieved_identity.id == identity_id

    mock_track.assert_called_once()

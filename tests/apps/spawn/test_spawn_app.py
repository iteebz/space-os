import pytest
from unittest.mock import patch
from pathlib import Path
import sqlite3
from datetime import datetime # Import datetime
import shutil # Import shutil

# Import RegistryRepo directly, not through registry_app
from space.apps.spawn.repo import SpawnRepo
from space.apps.spawn.models import Identity, Constitution
from space.os.lib import uuid7

@pytest.fixture
def clean_registry_db(tmp_path):
    """
    Provides a clean RegistryRepo instance with a temporary database for each test.
    """
    # Define the temporary database path
    temp_db_path = tmp_path / "spawn.db"

    # Define the actual app root path to copy migrations from
    actual_app_root = Path.cwd() / "space" / "apps" / "spawn"

    # Create a temporary directory for migrations within tmp_path
    temp_migrations_dir = tmp_path / "migrations" / "spawn"
    temp_migrations_dir.mkdir(parents=True, exist_ok=True)

    # Copy the migrations directory from the actual app to the temporary location
    shutil.copytree(actual_app_root / "migrations", temp_migrations_dir, dirs_exist_ok=True)

    # Create a SpawnRepo instance directly, passing the temporary db_path
    repo = SpawnRepo(db_path=temp_db_path)
    yield repo

    # Clean up: database will be removed with tmp_path

@pytest.fixture
def mock_uuid7():
    """
Mocks uuid7.uuid7() to return predictable UUIDs.

    The side_effect list provides a sequence of UUIDs that will be returned
    each time uuid7.uuid7() is called. This ensures deterministic UUIDs
    for testing purposes.
    """
    with patch('space.os.lib.uuid7.uuid7') as mock_uuid:
        mock_uuid.side_effect = [
            '00000000-0000-7000-8000-000000000001',
            '00000000-0000-7000-8000-000000000002',
            '00000000-0000-7000-8000-000000000003',
            '00000000-0000-7000-8000-000000000004',
            '00000000-0000-7000-8000-000000000005',
            '00000000-0000-7000-8000-000000000006',
            '00000000-0000-7000-8000-000000000007',
            '00000000-0000-7000-8000-000000000008',
            '00000000-0000-7000-8000-000000000009',
        ]
        yield

def test_add_and_get_identity(clean_registry_db, mock_uuid7):
    repo = clean_registry_db # The fixture now yields the repo directly
    identity_id = "test_agent_1"
    identity_type = "agent"

    # Add an identity
    added_identity = repo.add_identity(identity_id, identity_type)

    assert added_identity is not None
    assert added_identity.id == identity_id
    assert added_identity.type == identity_type
    assert added_identity.current_constitution_id is None

    # Get the identity
    retrieved_identity = repo.get_identity(identity_id)

    assert retrieved_identity is not None
    assert retrieved_identity.id == identity_id
    assert retrieved_identity.type == identity_type
    assert retrieved_identity.current_constitution_id is None
    assert retrieved_identity.created_at is not None
    assert retrieved_identity.updated_at is not None
    assert retrieved_identity.created_at == retrieved_identity.updated_at

def test_add_identity_with_initial_constitution(clean_registry_db, mock_uuid7):
    repo = clean_registry_db # The fixture now yields the repo directly
    identity_id = "test_agent_2"
    identity_type = "agent"
    initial_content = "This is the initial constitution for agent 2."

    # Add the identity first
    added_identity = repo.add_identity(identity_id, identity_type)

    # Add the constitution
    constitution = repo.add_constitution("initial_constitution", "1.0", initial_content, identity_id, created_by="test_user", change_description="Initial constitution")

    # Update the identity with the initial constitution
    repo.update_identity_current_constitution(identity_id, constitution.id)

    # Re-fetch the identity to get the updated current_constitution_id
    added_identity = repo.get_identity(identity_id)

    assert added_identity is not None
    assert added_identity.id == identity_id
    assert added_identity.type == identity_type
    assert added_identity.current_constitution_id is not None # Should now have a constitution

    # Get the identity again to confirm current_constitution_id
    retrieved_identity = repo.get_identity(identity_id)
    assert retrieved_identity.current_constitution_id == added_identity.current_constitution_id

    # Get the constitution
    constitution = repo.get_constitution_version(retrieved_identity.current_constitution_id)
    assert constitution is not None
    assert constitution.id == retrieved_identity.current_constitution_id
    assert constitution.name == "initial_constitution"
    assert constitution.content == initial_content
    assert constitution.identity_id == identity_id
    assert constitution.previous_version_id is None
    assert constitution.created_by == "test_user"
    assert constitution.change_description == "Initial constitution"

def test_add_constitution_to_existing_identity(clean_registry_db, mock_uuid7):
    repo = clean_registry_db
    identity_id = "test_agent_3"
    identity_type = "agent"
    initial_content = "Initial constitution for agent 3."
    new_content = "Updated constitution for agent 3."

    # Add the identity first
    added_identity = repo.add_identity(identity_id, identity_type)

    # Add an initial constitution
    initial_constitution = repo.add_constitution("initial_constitution", "1.0", initial_content, identity_id, created_by="test_user", change_description="Initial constitution")

    # Update the identity with the initial constitution
    repo.update_identity_current_constitution(identity_id, initial_constitution.id)
    initial_constitution_id = initial_constitution.id # Use the ID directly
    assert initial_constitution_id is not None

    # Add a new constitution to the existing identity
    new_constitution = repo.add_constitution(
        identity_id=identity_id,
        name=f"{identity_id}_constitution",
        version="V2",
        content=new_content,
        previous_version_id=initial_constitution_id, # <--- Add this line
        created_by="test_user",
        change_description="Updated constitution"
    )

    # Update the identity with the new constitution
    repo.update_identity_current_constitution(identity_id, new_constitution.id)

    # Re-fetch the identity to get the updated current_constitution_id
    updated_identity = repo.get_identity(identity_id)

    assert updated_identity is not None
    assert updated_identity.id == identity_id
    assert updated_identity.type == identity_type
    assert updated_identity.current_constitution_id != initial_constitution_id # Should be a new constitution

    # Get the latest constitution
    latest_constitution = repo.get_constitution_version(updated_identity.current_constitution_id)
    assert latest_constitution is not None
    assert latest_constitution.content == new_content
    assert latest_constitution.previous_version_id == initial_constitution_id

    # Verify the old constitution still exists
    old_constitution = repo.get_constitution_version(initial_constitution_id)
    assert old_constitution is not None
    assert old_constitution.content == initial_content
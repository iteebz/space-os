import contextlib
import sqlite3

import pytest

from space.spawn import registry, spawn


@pytest.fixture
def in_memory_db():
    # Create a single in-memory connection
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Temporarily override registry.get_db to return this connection
    original_get_db = registry.get_db

    @contextlib.contextmanager
    def mock_get_db():
        yield conn

    registry.get_db = mock_get_db

    # Initialize schema for both tables on this connection
    registry.init_db()

    yield conn

    conn.close()
    registry.get_db = original_get_db  # Restore original


def test_save_and_get_agent_identity(in_memory_db):
    sender_id = "test_agent"
    full_identity = "You are a test agent.\nSelf: I am a test.\n\nConstitution: Test."
    constitution_hash = spawn.hash_content(full_identity)

    # Test saving a new identity
    registry.save_agent_identity(sender_id, full_identity, constitution_hash)
    retrieved_identity = registry.get_agent_identity(sender_id)
    assert retrieved_identity == full_identity

    # Test updating an existing identity
    updated_full_identity = (
        "You are an updated test agent.\nSelf: I am updated.\n\nConstitution: Updated Test."
    )
    updated_constitution_hash = spawn.hash_content(updated_full_identity)
    registry.save_agent_identity(sender_id, updated_full_identity, updated_constitution_hash)
    retrieved_updated_identity = registry.get_agent_identity(sender_id)
    assert retrieved_updated_identity == updated_full_identity

    # Test getting a non-existent identity
    non_existent_identity = registry.get_agent_identity("non_existent_agent")
    assert non_existent_identity is None


def test_save_agent_identity_with_long_content(in_memory_db):
    sender_id = "long_content_agent"
    long_full_identity = "A" * 10000  # 10,000 characters
    constitution_hash = spawn.hash_content(long_full_identity)

    registry.save_agent_identity(sender_id, long_full_identity, constitution_hash)
    retrieved_identity = registry.get_agent_identity(sender_id)
    assert retrieved_identity == long_full_identity


def test_save_agent_identity_with_special_characters(in_memory_db):
    sender_id = "special_char_agent"
    special_char_identity = "Hello!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
    constitution_hash = spawn.hash_content(special_char_identity)

    registry.save_agent_identity(sender_id, special_char_identity, constitution_hash)
    retrieved_identity = registry.get_agent_identity(sender_id)
    assert retrieved_identity == special_char_identity


def test_save_and_get_constitution(in_memory_db):
    constitution_content = "This is a test constitution."
    constitution_hash = spawn.hash_content(constitution_content)

    # Test saving a new constitution
    registry.save_constitution(constitution_hash, constitution_content)
    retrieved_content = registry.get_constitution(constitution_hash)
    assert retrieved_content == constitution_content

    # Test saving the same constitution again (should be ignored due to INSERT OR IGNORE)
    registry.save_constitution(constitution_hash, "Modified content")
    retrieved_content_again = registry.get_constitution(constitution_hash)
    assert retrieved_content_again == constitution_content  # Should still be original content

    # Test getting a non-existent constitution
    non_existent_constitution = registry.get_constitution("non_existent_hash")
    assert non_existent_constitution is None


def test_save_constitution_with_long_content(in_memory_db):
    long_constitution_content = "B" * 20000  # 20,000 characters
    constitution_hash = spawn.hash_content(long_constitution_content)

    registry.save_constitution(constitution_hash, long_constitution_content)
    retrieved_content = registry.get_constitution(constitution_hash)
    assert retrieved_content == long_constitution_content


def test_save_constitution_with_special_characters(in_memory_db):
    special_char_constitution = "Constitution!@#$%^&*()_+-=[]{}\\|;':\",./<>?`~"
    constitution_hash = spawn.hash_content(special_char_constitution)

    registry.save_constitution(constitution_hash, special_char_constitution)
    retrieved_content = registry.get_constitution(constitution_hash)
    assert retrieved_content == special_char_constitution

import sqlite3
from unittest.mock import patch

import pytest
from space.registry import db as registry_db
from space.spawn import spawn

from space.lib import hashing


@pytest.fixture
def setup_test_spawn_db(tmp_path):
    """Set up a temporary spawn.db for testing."""
    test_db_path = tmp_path / "spawn.db"
    with patch("space.spawn.config.registry_db", return_value=test_db_path):
        registry.init_db()
        yield test_db_path


@pytest.fixture
def setup_test_constitutions_db(tmp_path):
    """Set up a temporary constitutions.db for testing."""
    test_db_path = tmp_path / "registry.db"
    with patch("space.registry.db.database_path", return_value=test_db_path):
        registry_db._ensure_registry_db()
        yield test_db_path


def test_register_agent_autoregisters_constitution(
    setup_test_spawn_db, setup_test_constitutions_db, tmp_path
):
    role = "test_role"
    sender_id = "test_agent"
    topic = "test_topic"
    constitution_content = "You are a test agent. Be helpful."

    # Create a dummy constitution file
    dummy_constitution_path = tmp_path / "dummy_constitution.md"
    dummy_constitution_path.write_text(constitution_content)

    with patch("space.spawn.spawner.get_constitution_path", return_value=dummy_constitution_path):
        spawn(role, sender_id, topic)

    # Verify constitution was registered in constitutions.db
    conn = sqlite3.connect(setup_test_constitutions_db)
    cursor = conn.execute(
        "SELECT hash, content FROM constitutions WHERE hash = ?",
        (hashing.sha256(constitution_content),),
    )
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == hashing.sha256(constitution_content)
    assert result[1] == constitution_content


def test_register_agent_uses_correct_constitution_hash_in_registry(
    setup_test_spawn_db, setup_test_constitutions_db, tmp_path
):
    role = "test_role_hash"
    sender_id = "test_agent_hash"
    topic = "test_topic_hash"
    constitution_content = "You are a test agent for hash verification."

    dummy_constitution_path = tmp_path / "dummy_constitution_hash.md"
    dummy_constitution_path.write_text(constitution_content)

    with patch("space.spawn.spawner.get_constitution_path", return_value=dummy_constitution_path):
        result = spawn(role, sender_id, topic)

    # Verify the constitution_hash returned by register_agent
    expected_full_hash = hashing.sha256(constitution_content)
    expected_truncated_hash = hashing.sha256(constitution_content, 8)

    assert result["constitution_hash"] == expected_truncated_hash

    # Verify the identity_hash stored in spawn.db registry
    conn = sqlite3.connect(setup_test_spawn_db)
    cursor = conn.execute(
        "SELECT identity_hash FROM registrations WHERE sender_id = ?", (sender_id,)
    )
    reg_identity_hash = cursor.fetchone()[0]
    conn.close()

    assert reg_identity_hash == expected_full_hash

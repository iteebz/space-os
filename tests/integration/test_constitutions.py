import time
from unittest.mock import patch

import pytest
from space.apps.register import db as registry_db

from space.lib import hashing


@pytest.fixture
def setup_test_constitutions_db(tmp_path):
    """Set up a temporary constitutions.db for testing."""
    test_db_path = tmp_path / "registry.db"
    with patch("space.registry.db.database_path", return_value=test_db_path):
        registry_db._ensure_registry_db()
        yield test_db_path


def test_track_constitution(setup_test_constitutions_db):
    content = "This is the content of a test constitution."
    registry_db.track_constitution(hashing.sha256(content), content)

    conn = sqlite3.connect(setup_test_constitutions_db)
    cursor = conn.execute(
        "SELECT hash, content FROM constitutions WHERE hash = ?", (hashing.sha256(content),)
    )
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == hashing.sha256(content)
    assert result[1] == content


def test_track_constitution_idempotency(setup_test_constitutions_db):
    content = "Content for idempotency test."

    registry_db.track_constitution(hashing.sha256(content), content)
    conn = sqlite3.connect(setup_test_constitutions_db)
    cursor = conn.execute(
        "SELECT COUNT(*) FROM constitutions WHERE hash = ?", (hashing.sha256(content),)
    )
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1  # Should only be one entry due to UNIQUE constraint


def test_track_constitution_new_version(setup_test_constitutions_db):
    content_v1 = "Version 1 content."
    content_v2 = "Version 2 content."

    registry_db.track_constitution(hashing.sha256(content_v1), content_v1)
    time.sleep(0.1)  # Ensure different created_at timestamp
    registry_db.track_constitution(hashing.sha256(content_v2), content_v2)

    conn = registry_db.sqlite3.connect(setup_test_constitutions_db)
    cursor = conn.execute(
        "SELECT hash, content FROM constitutions WHERE hash = ?", (hashing.sha256(content_v2),)
    )
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == hashing.sha256(content_v2)
    assert result[1] == content_v2


def test_get_current_hash(setup_test_constitutions_db):
    content_old = "Old content."
    content_new = "New content."

    registry_db.track_constitution(hashing.sha256(content_old), content_old)
    time.sleep(0.1)
    registry_db.track_constitution(hashing.sha256(content_new), content_new)

    current_hash = registry_db.get_constitution_content(hashing.sha256(content_new))
    assert current_hash == content_new


def test_get_current_hash_non_existent(setup_test_constitutions_db):
    current_hash = registry_db.get_constitution_content(hashing.sha256("non_existent_constitution"))
    assert current_hash is None


def test_list_constitutions(setup_test_constitutions_db):
    registry_db.track_constitution(hashing.sha256("Content A"), "Content A")
    time.sleep(0.1)
    registry_db.track_constitution(hashing.sha256("Content B"), "Content B")
    time.sleep(0.1)
    registry_db.track_constitution(hashing.sha256("Content A updated"), "Content A updated")

    listed = registry_db.list_constitutions()
    # Should return all constitutions
    assert len(listed) == 3

    hashes = {c[0] for c in listed}
    assert hashing.sha256("Content A") in hashes
    assert hashing.sha256("Content B") in hashes
    assert hashing.sha256("Content A updated") in hashes

    # Verify content for one of the constitutions
    for hash_val, content in listed:
        if hash_val == hashing.sha256("Content A updated"):
            assert content == "Content A updated"

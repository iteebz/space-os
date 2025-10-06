import time
from pathlib import Path
from unittest.mock import patch

import pytest

from space.lib.storage import constitutions


@pytest.fixture
def setup_test_constitutions_db(tmp_path):
    """Set up a temporary constitutions.db for testing."""
    test_db_path = tmp_path / "constitutions.db"
    with patch("space.lib.storage.constitutions.DB_PATH", new=test_db_path):
        constitutions._init_db()
        yield test_db_path


def test_track_constitution(setup_test_constitutions_db):
    name = "test_constitution"
    content = "This is the content of a test constitution."

    constitutions.track(name, content)

    conn = constitutions.sqlite3.connect(setup_test_constitutions_db)
    cursor = conn.execute("SELECT name, hash, created_at FROM constitution_versions WHERE name = ?", (name,))
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == name
    assert result[1] == constitutions.hash.sha256(content, 16)
    assert isinstance(result[2], int)


def test_track_constitution_idempotency(setup_test_constitutions_db):
    name = "idempotent_constitution"
    content = "Content for idempotency test."

    constitutions.track(name, content)
    constitutions.track(name, content)  # Track again with same content

    conn = constitutions.sqlite3.connect(setup_test_constitutions_db)
    cursor = conn.execute("SELECT COUNT(*) FROM constitution_versions WHERE name = ?", (name,))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1  # Should only be one entry due to UNIQUE constraint


def test_track_constitution_new_version(setup_test_constitutions_db):
    name = "versioned_constitution"
    content_v1 = "Version 1 content."
    content_v2 = "Version 2 content."

    constitutions.track(name, content_v1)
    time.sleep(0.1)  # Ensure different created_at timestamp
    constitutions.track(name, content_v2)

    conn = constitutions.sqlite3.connect(setup_test_constitutions_db)
    cursor = conn.execute("SELECT hash FROM constitution_versions WHERE name = ? ORDER BY created_at DESC", (name,))
    results = cursor.fetchall()
    conn.close()

    assert len(results) == 2
    assert results[0][0] == constitutions.hash.sha256(content_v2, 16)
    assert results[1][0] == constitutions.hash.sha256(content_v1, 16)


def test_get_current_hash(setup_test_constitutions_db):
    name = "current_hash_test"
    content_old = "Old content."
    content_new = "New content."

    constitutions.track(name, content_old)
    time.sleep(0.1)
    constitutions.track(name, content_new)

    current_hash = constitutions.get_current_hash(name)
    assert current_hash == constitutions.hash.sha256(content_new, 16)


def test_get_current_hash_non_existent(setup_test_constitutions_db):
    current_hash = constitutions.get_current_hash("non_existent_constitution")
    assert current_hash is None


def test_list_constitutions(setup_test_constitutions_db):
    constitutions.track("const_a", "Content A")
    time.sleep(0.1)
    constitutions.track("const_b", "Content B")
    time.sleep(0.1)
    constitutions.track("const_a", "Content A updated")

    listed = constitutions.list_constitutions()
    # Should return the latest version of each unique constitution name
    assert len(listed) == 2

    names = {c[0] for c in listed}
    assert "const_a" in names
    assert "const_b" in names

    # Verify latest hash for const_a
    for name, hash_val, _ in listed:
        if name == "const_a":
            assert hash_val == constitutions.hash.sha256("Content A updated", 16)
        if name == "const_b":
            assert hash_val == constitutions.hash.sha256("Content B", 16)

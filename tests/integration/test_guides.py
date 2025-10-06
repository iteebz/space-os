import sqlite3
import time
from unittest.mock import patch

import pytest

from space.lib import hashing
from space.registry import db as registry_db


@pytest.fixture
def setup_test_guides_db(tmp_path):
    """Set up a temporary guides.db for testing."""
    test_db_path = tmp_path / "registry.db"
    with patch("space.registry.db.database_path", return_value=test_db_path):
        registry_db._ensure_registry_db()
        yield test_db_path


def test_track_guide(setup_test_guides_db):
    name = "test_guide"
    content = "This is the content of a test guide."

    registry_db.add_guide(name, content, hashing.sha256(content, 16))

    conn = sqlite3.connect(setup_test_guides_db)
    cursor = conn.execute(
        "SELECT name, content, hash, created_at FROM guides WHERE name = ?", (name,)
    )
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == name
    assert result[1] == content
    assert result[2] == hashing.sha256(content, 16)
    assert isinstance(result[3], int)


def test_track_guide_idempotency(setup_test_guides_db):
    name = "idempotent_guide"
    content = "Content for idempotency test."

    registry_db.add_guide(name, content, hashing.sha256(content, 16))
    registry_db.add_guide(
        name, content, hashing.sha256(content, 16)
    )  # Track again with same content

    conn = sqlite3.connect(setup_test_guides_db)
    cursor = conn.execute("SELECT COUNT(*) FROM guides WHERE name = ?", (name,))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1  # Should only be one entry due to PRIMARY KEY constraint


def test_track_guide_new_version(setup_test_guides_db):
    name = "versioned_guide"
    content_v1 = "Version 1 content."
    content_v2 = "Version 2 content."

    registry_db.add_guide(name, content_v1, hashing.sha256(content_v1, 16))
    time.sleep(0.1)  # Ensure different created_at timestamp
    registry_db.add_guide(name, content_v2, hashing.sha256(content_v2, 16))

    conn = sqlite3.connect(setup_test_guides_db)
    cursor = conn.execute(
        "SELECT hash, content FROM guides WHERE name = ? ORDER BY created_at DESC", (name,)
    )
    results = cursor.fetchall()
    conn.close()

    assert len(results) == 1  # Only one entry due to REPLACE
    assert results[0][0] == hashing.sha256(content_v2, 16)
    assert results[0][1] == content_v2


def test_get_current_hash(setup_test_guides_db):
    name = "current_hash_test"
    content_old = "Old content."
    content_new = "New content."

    registry_db.add_guide(name, content_old, hashing.sha256(content_old, 16))
    time.sleep(0.1)
    registry_db.add_guide(name, content_new, hashing.sha256(content_new, 16))

    current_content = registry_db.get_guide_content(name)
    assert current_content == content_new


def test_get_current_hash_non_existent(setup_test_guides_db):
    current_content = registry_db.get_guide_content("non_existent_guide")
    assert current_content is None


def test_list_guides(setup_test_guides_db):
    registry_db.add_guide("guide_a", "Content A", hashing.sha256("Content A", 16))
    time.sleep(0.1)
    registry_db.add_guide("guide_b", "Content B", hashing.sha256("Content B", 16))
    time.sleep(0.1)
    registry_db.add_guide("guide_a", "Content A updated", hashing.sha256("Content A updated", 16))

    listed = registry_db.list_guides()
    assert len(listed) == 2

    names = {c[0] for c in listed}
    assert "guide_a" in names
    assert "guide_b" in names

    for name, content, hash_val, _ in listed:
        if name == "guide_a":
            assert hash_val == hashing.sha256("Content A updated", 16)
            assert content == "Content A updated"
        if name == "guide_b":
            assert hash_val == hashing.sha256("Content B", 16)
            assert content == "Content B"

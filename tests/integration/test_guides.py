import time
from pathlib import Path
from unittest.mock import patch

import pytest

from space.lib.storage import guides


@pytest.fixture
def setup_test_guides_db(tmp_path):
    """Set up a temporary guides.db for testing."""
    test_db_path = tmp_path / "guides.db"
    with patch("space.lib.storage.guides.DB_PATH", new=test_db_path):
        guides._init_db()
        yield test_db_path


def test_track_guide(setup_test_guides_db):
    name = "test_guide"
    content = "This is the content of a test guide."

    guides.track(name, content)

    conn = guides.sqlite3.connect(setup_test_guides_db)
    cursor = conn.execute("SELECT name, hash, created_at FROM guide_versions WHERE name = ?", (name,))
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == name
    assert result[1] == guides.hash.sha256(content, 16)
    assert isinstance(result[2], int)


def test_track_guide_idempotency(setup_test_guides_db):
    name = "idempotent_guide"
    content = "Content for idempotency test."

    guides.track(name, content)
    guides.track(name, content)  # Track again with same content

    conn = guides.sqlite3.connect(setup_test_guides_db)
    cursor = conn.execute("SELECT COUNT(*) FROM guide_versions WHERE name = ?", (name,))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1  # Should only be one entry due to UNIQUE constraint


def test_track_guide_new_version(setup_test_guides_db):
    name = "versioned_guide"
    content_v1 = "Version 1 content."
    content_v2 = "Version 2 content."

    guides.track(name, content_v1)
    time.sleep(0.1)  # Ensure different created_at timestamp
    guides.track(name, content_v2)

    conn = guides.sqlite3.connect(setup_test_guides_db)
    cursor = conn.execute("SELECT hash FROM guide_versions WHERE name = ? ORDER BY created_at DESC", (name,))
    results = cursor.fetchall()
    conn.close()

    assert len(results) == 2
    assert results[0][0] == guides.hash.sha256(content_v2, 16)
    assert results[1][0] == guides.hash.sha256(content_v1, 16)


def test_get_current_hash(setup_test_guides_db):
    name = "current_hash_test"
    content_old = "Old content."
    content_new = "New content."

    guides.track(name, content_old)
    time.sleep(0.1)
    guides.track(name, content_new)

    current_hash = guides.get_current_hash(name)
    assert current_hash == guides.hash.sha256(content_new, 16)


def test_get_current_hash_non_existent(setup_test_guides_db):
    current_hash = guides.get_current_hash("non_existent_guide")
    assert current_hash is None


def test_list_guides(setup_test_guides_db):
    guides.track("guide_a", "Content A")
    time.sleep(0.1)
    guides.track("guide_b", "Content B")
    time.sleep(0.1)
    guides.track("guide_a", "Content A updated")

    listed = guides.list_guides()
    # Should return the latest version of each unique guide name
    assert len(listed) == 2

    names = {c[0] for c in listed}
    assert "guide_a" in names
    assert "guide_b" in names

    # Verify latest hash for guide_a
    for name, hash_val, _ in listed:
        if name == "guide_a":
            assert hash_val == guides.hash.sha256("Content A updated", 16)
        if name == "guide_b":
            assert hash_val == guides.hash.sha256("Content B", 16)

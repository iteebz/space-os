"""Tests for space.lib.store.health module."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from space.lib.store.health import (
    check_backup_has_data,
    compare_snapshots,
    get_backup_stats,
)


@pytest.fixture
def temp_backup_dir():
    """Create temporary directory for backup databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_check_backup_has_data_nonexistent(temp_backup_dir):
    """Test check returns False for nonexistent backup."""
    result = check_backup_has_data(temp_backup_dir, "missing.db")
    assert result is False


def test_check_backup_has_data_empty(temp_backup_dir):
    """Test check returns False for database with no tables."""
    db_file = temp_backup_dir / "empty.db"
    conn = sqlite3.connect(db_file)
    conn.close()

    result = check_backup_has_data(temp_backup_dir, "empty.db")
    assert result is False


def test_check_backup_has_data_with_data(temp_backup_dir):
    """Test check returns True for database with data."""
    db_file = temp_backup_dir / "data.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE test (id INTEGER, value TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'hello')")
    conn.commit()
    conn.close()

    result = check_backup_has_data(temp_backup_dir, "data.db")
    assert result is True


def test_get_backup_stats_nonexistent(temp_backup_dir):
    """Test stats returns empty dict for nonexistent backup."""
    stats = get_backup_stats(temp_backup_dir, "missing.db")
    assert stats == {}


def test_get_backup_stats_with_data(temp_backup_dir):
    """Test stats returns table counts."""
    db_file = temp_backup_dir / "data.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE users (id INTEGER)")
    conn.execute("CREATE TABLE posts (id INTEGER)")
    conn.execute("INSERT INTO users VALUES (1)")
    conn.execute("INSERT INTO users VALUES (2)")
    conn.execute("INSERT INTO posts VALUES (1)")
    conn.commit()
    conn.close()

    stats = get_backup_stats(temp_backup_dir, "data.db")
    assert stats == {"users": 2, "posts": 1}


def test_compare_snapshots_no_change():
    """Test compare returns empty list when nothing changed."""
    before = {"db1": 100, "db2": 50}
    after = {"db1": 100, "db2": 50}

    warnings = compare_snapshots(before, after)
    assert warnings == []


def test_compare_snapshots_significant_loss():
    """Test compare detects significant data loss."""
    before = {"db1": 100}
    after = {"db1": 10}

    warnings = compare_snapshots(before, after, threshold=0.8)
    assert len(warnings) == 1
    assert "90%" in warnings[0]


def test_compare_snapshots_complete_loss():
    """Test compare detects complete database loss."""
    before = {"db1": 100}
    after = {"db1": 0}

    warnings = compare_snapshots(before, after)
    assert len(warnings) == 1
    assert "completely emptied" in warnings[0]


def test_compare_snapshots_new_db():
    """Test compare allows new databases."""
    before = {}
    after = {"db2": 50}

    warnings = compare_snapshots(before, after)
    assert warnings == []

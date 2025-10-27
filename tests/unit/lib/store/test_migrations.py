"""Tests for space.lib.store.migrations module."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from space.lib.store import migrations


@pytest.fixture
def temp_db_dir():
    """Create temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_ensure_schema_creates_database(temp_db_dir):
    """Test ensure_schema creates database file."""
    db_path = temp_db_dir / "test.db"
    assert not db_path.exists()

    migrations.ensure_schema(db_path)

    assert db_path.exists()


def test_ensure_schema_applies_migrations(temp_db_dir):
    """Test ensure_schema applies migrations."""
    db_path = temp_db_dir / "test.db"
    migs = [
        ("init", "CREATE TABLE test (id TEXT PRIMARY KEY)"),
        ("v1", "ALTER TABLE test ADD COLUMN value TEXT"),
    ]

    migrations.ensure_schema(db_path, migs)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(test)")
    columns = {row[1] for row in cursor.fetchall()}
    assert "id" in columns
    assert "value" in columns
    conn.close()


def test_migrate_callable(temp_db_dir):
    """Test migrate with callable migration."""
    db_path = temp_db_dir / "test.db"

    def create_table(conn):
        conn.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")

    migs = [("init", create_table)]
    migrations.ensure_schema(db_path, migs)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "test" in tables
    conn.close()


def test_migrate_multiple_statements(temp_db_dir):
    """Test migrate with multiple SQL statements."""
    db_path = temp_db_dir / "test.db"
    sql = "CREATE TABLE t1 (id INT); CREATE TABLE t2 (id INT);"
    migs = [("init", sql)]

    migrations.ensure_schema(db_path, migs)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "t1" in tables
    assert "t2" in tables
    conn.close()


def test_migrate_idempotent(temp_db_dir):
    """Test migrations are applied only once."""
    db_path = temp_db_dir / "test.db"
    migs = [("init", "CREATE TABLE test (id TEXT PRIMARY KEY)")]

    migrations.ensure_schema(db_path, migs)
    migrations.ensure_schema(db_path, migs)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    table_count = tables.count("test")
    assert table_count == 1
    conn.close()


def test_migrate_tracks_applied(temp_db_dir):
    """Test migrations are tracked in _migrations table."""
    db_path = temp_db_dir / "test.db"
    migs = [("v1", "CREATE TABLE test (id TEXT)")]

    migrations.ensure_schema(db_path, migs)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM _migrations")
    applied = {row[0] for row in cursor.fetchall()}
    assert "v1" in applied
    conn.close()


def test_migrate_data_loss_detection(temp_db_dir):
    """Test migration fails if data is lost unexpectedly."""
    db_path = temp_db_dir / "test.db"

    def drop_data(conn):
        conn.execute("DELETE FROM test")

    migs = [
        ("init", "CREATE TABLE test (id TEXT PRIMARY KEY)"),
        ("bad", drop_data),
    ]

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO test VALUES ('x')")
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="rows lost"):
        migrations.migrate(sqlite3.connect(db_path), migs[1:])

"""Tests for space.lib.sqlite backend."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from space.lib import sqlite, store


@pytest.fixture
def temp_db_dir():
    """Create temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def clean_registry():
    """Clear registry before and after each test."""
    store._reset_for_testing()
    yield
    store._reset_for_testing()


def test_connect_basic(temp_db_dir):
    """Test basic connection to SQLite database."""
    db_path = temp_db_dir / "test.db"
    conn = sqlite.connect(db_path)

    assert isinstance(conn, sqlite3.Connection)
    assert conn.row_factory == sqlite3.Row
    conn.close()
    assert db_path.exists()


def test_register_database(clean_registry):
    """Test registering a database."""
    store.register("test_db", "test.db")

    assert "test_db" in store._registry
    assert store._registry["test_db"] == "test.db"


def test_register_migrations(clean_registry):
    """Test registering migrations."""
    migs = [("v1", "CREATE TABLE test (id TEXT)")]
    store.add_migrations("test_db", migs)

    assert "test_db" in store._migrations
    assert store._migrations["test_db"] == migs


def test_ensure_unregistered_raises(clean_registry, temp_db_dir, monkeypatch):
    """Test ensure raises error for unregistered database."""
    monkeypatch.setattr("space.lib.paths.dot_space", lambda: temp_db_dir)

    with pytest.raises(ValueError, match="not registered"):
        store.ensure("nonexistent")


def test_ensure_creates_schema(clean_registry, temp_db_dir, monkeypatch):
    """Test ensure creates schema for new database."""
    monkeypatch.setattr("space.lib.paths.dot_space", lambda: temp_db_dir)

    migs = [("init", "CREATE TABLE test (id TEXT PRIMARY KEY, value TEXT)")]
    store.register("test_db", "test.db")
    store.add_migrations("test_db", migs)

    conn = store.ensure("test_db")

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "test" in tables

    conn.close()


def test_migrate_basic(clean_registry, temp_db_dir, monkeypatch):
    """Test basic migration."""
    monkeypatch.setattr("space.lib.paths.dot_space", lambda: temp_db_dir)

    migs = [
        ("init", "CREATE TABLE test (id TEXT PRIMARY KEY)"),
        ("add_value", "ALTER TABLE test ADD COLUMN value TEXT"),
    ]
    store.register("test_db", "test.db")
    store.add_migrations("test_db", migs)

    conn = store.ensure("test_db")

    cursor = conn.execute("PRAGMA table_info(test)")
    columns = {row[1] for row in cursor.fetchall()}
    assert "value" in columns

    conn.close()


def test_migrate_callable(clean_registry, temp_db_dir, monkeypatch):
    """Test migration with callable."""
    monkeypatch.setattr("space.lib.paths.dot_space", lambda: temp_db_dir)

    def add_column(conn):
        conn.execute("ALTER TABLE test ADD COLUMN computed TEXT")

    migs = [("init", "CREATE TABLE test (id TEXT PRIMARY KEY)"), ("add_computed", add_column)]
    store.register("test_db", "test.db")
    store.add_migrations("test_db", migs)

    conn = store.ensure("test_db")

    cursor = conn.execute("PRAGMA table_info(test)")
    columns = {row[1] for row in cursor.fetchall()}
    assert "computed" in columns

    conn.close()


def test_migrate_skips_applied(clean_registry, temp_db_dir, monkeypatch):
    """Test migrations are applied only once."""
    monkeypatch.setattr("space.lib.paths.dot_space", lambda: temp_db_dir)

    call_count = 0

    def track_call(conn):
        nonlocal call_count
        call_count += 1

    migs = [("init", "CREATE TABLE test (id TEXT PRIMARY KEY)"), ("track", track_call)]
    store.register("test_db", "test.db")
    store.add_migrations("test_db", migs)

    store.ensure("test_db")
    assert call_count == 1

    store.ensure("test_db")
    assert call_count == 1


def test_ensure_schema_with_migrations(clean_registry, temp_db_dir):
    """Test ensure_schema applies migrations."""
    db_path = temp_db_dir / "test.db"
    migs = [
        ("init", "CREATE TABLE test (id TEXT PRIMARY KEY)"),
        ("v1", "ALTER TABLE test ADD COLUMN value TEXT"),
    ]

    sqlite.ensure_schema(db_path, migs)

    conn = sqlite.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(test)")
    columns = {row[1] for row in cursor.fetchall()}
    assert "value" in columns
    conn.close()

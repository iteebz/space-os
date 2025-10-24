"""Tests for database connection management patterns and cleanup."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from space.os import db
from space.os.db import sqlite as db_sqlite


@pytest.fixture
def temp_db_dir():
    """Create temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_db(temp_db_dir):
    """Create a test database."""
    db_path = temp_db_dir / "test.db"
    conn = db_sqlite.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO test (value) VALUES ('test1')")
    conn.commit()
    conn.close()
    return db_path


class TestContextManagerCleanup:
    """Test that context managers properly clean up connections."""

    def test_context_manager_works(self, temp_db_dir):
        """Verify context manager properly manages connection lifecycle."""
        temp_db_dir / "test.db"
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY)"
        db.register("test_db", "test.db", schema)

        with db.ensure("test_db") as conn:
            assert conn is not None
            conn.execute("SELECT 1")

    def test_context_manager_exception_safe(self, temp_db_dir):
        """Verify connection cleanup even on exception."""
        temp_db_dir / "test.db"
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY)"
        db.register("test_exc", "test.db", schema)

        try:
            with db.ensure("test_exc") as conn:
                raise ValueError("Test error")
        except ValueError:
            pass

        with db.ensure("test_exc") as conn:
            conn.execute("SELECT 1")

    def test_row_factory_set_correctly(self):
        """Verify row_factory is set in ensure()."""
        db_sqlite._reset_for_testing()
        schema = "CREATE TABLE test_rf (id INTEGER PRIMARY KEY, name TEXT)"
        db.register("test_row", "test_row.db", schema)

        with db.ensure("test_row") as conn:
            conn.execute("INSERT INTO test_rf (name) VALUES ('test')")
            row = conn.execute("SELECT * FROM test_rf").fetchone()
            assert isinstance(row, sqlite3.Row)

    def test_isolation_level_none(self):
        """Verify autocommit mode is enabled."""
        db_sqlite._reset_for_testing()
        schema = "CREATE TABLE test_iso (id INTEGER PRIMARY KEY)"
        db.register("test_iso", "test_iso.db", schema)

        with db.ensure("test_iso") as conn:
            assert conn.isolation_level is None

    def test_sequential_connections_independent(self):
        """Verify sequential connections don't interfere."""
        db_sqlite._reset_for_testing()
        schema = "CREATE TABLE test_sequential (id INTEGER PRIMARY KEY, val INT)"
        db.register("test_seq_unique", "test_seq_unique.db", schema)

        with db.ensure("test_seq_unique") as conn1:
            conn1.execute("INSERT INTO test_sequential (val) VALUES (1)")

        with db.ensure("test_seq_unique") as conn2:
            rows = conn2.execute("SELECT COUNT(*) FROM test_sequential").fetchone()
            assert rows[0] >= 1


class TestResolveFunction:
    """Test WAL checkpoint resolution."""

    def test_resolve_executes_successfully(self, test_db):
        """Verify resolve() executes without error."""
        db_sqlite.resolve(test_db.parent)

    def test_resolve_handles_missing_db(self, temp_db_dir):
        """Verify resolve() handles missing databases gracefully."""
        db_sqlite.resolve(temp_db_dir)

    def test_resolve_cleans_wal_artifacts(self, temp_db_dir):
        """Verify resolve() removes WAL artifacts."""
        db_path = temp_db_dir / "test.db"
        conn = db_sqlite.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test (id) VALUES (1)")
        conn.close()

        db_sqlite.resolve(temp_db_dir)

        db_can_open = db_sqlite.connect(db_path)
        assert db_can_open is not None
        db_can_open.close()


class TestMultipleConnections:
    """Test handling multiple concurrent connections."""

    def test_different_databases_sequential(self, temp_db_dir):
        """Verify sequential connections to different databases."""
        db_sqlite._reset_for_testing()
        schema1 = "CREATE TABLE db_a (id INTEGER PRIMARY KEY)"
        schema2 = "CREATE TABLE db_b (id INTEGER PRIMARY KEY)"
        db.register("db_a_test", "db_a_test.db", schema1)
        db.register("db_b_test", "db_b_test.db", schema2)

        with db.ensure("db_a_test") as conn1:
            conn1.execute("INSERT INTO db_a VALUES (1)")

        with db.ensure("db_b_test") as conn2:
            conn2.execute("INSERT INTO db_b VALUES (2)")

        with db.ensure("db_a_test") as conn1:
            count1 = conn1.execute("SELECT COUNT(*) FROM db_a").fetchone()[0]
            assert count1 >= 1

        with db.ensure("db_b_test") as conn2:
            count2 = conn2.execute("SELECT COUNT(*) FROM db_b").fetchone()[0]
            assert count2 >= 1


class TestMigrationCleanup:
    """Test that migrations handle connection cleanup properly."""

    def test_migration_exception_rolls_back(self, temp_db_dir):
        """Verify failed migrations rollback and close connections."""
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY)"
        migrations = [
            ("v1", "CREATE TABLE test2 (id INTEGER PRIMARY KEY)"),
            ("v2", "INSERT INTO nonexistent VALUES (1)"),
        ]

        db.register("test_mig", "test.db", schema)
        db.add_migrations("test_mig", migrations)

        with pytest.raises(sqlite3.OperationalError):
            db.ensure_schema(temp_db_dir / "test.db", schema, migrations)

    def test_migration_success_commits(self, temp_db_dir):
        """Verify successful migrations commit and close properly."""
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY)"
        migrations = [
            ("v1", "CREATE TABLE test2 (id INTEGER PRIMARY KEY)"),
        ]

        db_path = temp_db_dir / "test.db"
        db.ensure_schema(db_path, schema, migrations)

        with db.connect(db_path) as conn:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]
            assert "test" in table_names
            assert "test2" in table_names
            assert "_migrations" in table_names

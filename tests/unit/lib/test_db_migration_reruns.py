import sqlite3
import tempfile
from pathlib import Path


def test_migrations_rerun_on_existing_database(monkeypatch):
    """Migrations should execute on existing databases, not just on first creation."""
    from space.lib import db
    from space.lib import paths as lib_paths

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        monkeypatch.setattr(lib_paths, "dot_space", lambda x=None: tmpdir)

        call_log = []

        def track_migration(conn):
            call_log.append("mig_called")
            conn.execute("CREATE TABLE IF NOT EXISTS tracked_mig (id INT)")

        db.register("test_rerun", "test_rerun.db", "")
        db.migrations("test_rerun", [("track_mig", track_migration)])

        conn1 = db.ensure("test_rerun")
        conn1.close()

        assert len(call_log) == 1, "Migration should run on first ensure()"

        conn2 = db.ensure("test_rerun")
        conn2.close()

        assert len(call_log) == 1, "Migration should NOT rerun (idempotent via _migrations table)"


def test_new_schema_applied_to_existing_database(monkeypatch):
    """New migrations added to existing database should execute on next ensure()."""
    from space.lib import db
    from space.lib import paths as lib_paths

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        monkeypatch.setattr(lib_paths, "dot_space", lambda x=None: tmpdir)

        db.register("test_schema", "test_schema.db", "CREATE TABLE IF NOT EXISTS initial (id INT)")
        db.migrations("test_schema", [("initial_mig", "CREATE TABLE IF NOT EXISTS t1 (id INT)")])

        conn1 = db.ensure("test_schema")
        conn1.close()

        cursor = sqlite3.connect(tmpdir / "test_schema.db").execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='t1'"
        )
        assert cursor.fetchone() is not None, "t1 should exist after first ensure"

        db.migrations(
            "test_schema",
            [
                ("initial_mig", "CREATE TABLE IF NOT EXISTS t1 (id INT)"),
                ("new_mig", "CREATE TABLE IF NOT EXISTS t2 (id INT)"),
            ],
        )

        conn2 = db.ensure("test_schema")
        conn2.close()

        cursor = sqlite3.connect(tmpdir / "test_schema.db").execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='t2'"
        )
        assert cursor.fetchone() is not None, (
            "t2 should exist after second ensure with new migration"
        )


def test_migration_runs_exactly_once(monkeypatch):
    """A migration should run exactly once, even if ensure() called multiple times."""
    from space.lib import db
    from space.lib import paths as lib_paths

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        monkeypatch.setattr(lib_paths, "dot_space", lambda x=None: tmpdir)

        call_count = {"count": 0}

        def counting_migration(conn):
            call_count["count"] += 1
            conn.execute("CREATE TABLE IF NOT EXISTS counter (id INT)")

        db.register("test_count", "test_count.db", "")
        db.migrations("test_count", [("count_mig", counting_migration)])

        for _ in range(5):
            conn = db.ensure("test_count")
            conn.close()

        assert call_count["count"] == 1, (
            f"Migration should run exactly once, ran {call_count['count']} times"
        )

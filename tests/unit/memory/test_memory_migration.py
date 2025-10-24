import sqlite3


def test_memory_migration_preserves_data():
    """Regression test: Memory migration should handle old 'memory' table correctly."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE memory (
            uuid TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            archived_at INTEGER,
            core INTEGER DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'manual',
            bridge_channel TEXT,
            code_anchors TEXT,
            synthesis_note TEXT
        );
        INSERT INTO memory (uuid, agent_id, topic, message, timestamp, created_at, core, source)
        VALUES ('mem-1', 'agent-1', 'test-topic', 'test message', '2025-10-21 10:00', 1729517000, 1, 'manual');
    """)
    conn.commit()

    from space.os.memory.db import _migrate_memory_table_to_memories

    _migrate_memory_table_to_memories(conn)

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory'")
    assert cursor.fetchone() is None, "Old memory table should be dropped"

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
    assert cursor.fetchone() is not None, "New memories table should exist"

    row = conn.execute(
        "SELECT memory_id, agent_id, topic, message, core FROM memories WHERE memory_id = 'mem-1'"
    ).fetchone()
    assert row is not None
    assert row["message"] == "test message"
    assert row["core"] == 1

    conn.close()


def test_memory_migration_idempotent():
    """Regression test: Memory migration should be safe to run multiple times."""
    import shutil
    import tempfile
    from pathlib import Path

    from space.os import db
    from space.os.memory import db as memory_db

    tmpdir = tempfile.mkdtemp()
    try:
        db_path = Path(tmpdir) / "memory.db"

        conn = db.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(memory_db._MEMORY_SCHEMA)
        conn.commit()

        # Test that migration idempotency—running same migrations twice
        # should only record them once
        test_migs = [("test_migration", "SELECT 1")]
        with conn:
            db.migrate(conn, test_migs)
            db.migrate(conn, test_migs)

        migrations_cursor = conn.execute(
            "SELECT COUNT(*) FROM _migrations WHERE name='test_migration'"
        )
        count = migrations_cursor.fetchone()[0]
        assert count == 1, "Migration should only be recorded once"

        conn.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

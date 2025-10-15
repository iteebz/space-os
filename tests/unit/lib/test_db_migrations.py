import sqlite3

import pytest

from space.bridge import db as bridge_db
from space.lib import db


@pytest.fixture
def in_memory_bridge_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(bridge_db._SCHEMA)
    conn.commit()
    yield conn
    conn.close()


def test_bridge_db_migration_converts_messages_id_to_text(in_memory_bridge_db):
    conn = in_memory_bridge_db

    # Manually create a messages table with INTEGER id to simulate old schema
    conn.executescript("""
        DROP TABLE IF EXISTS messages;
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            priority TEXT DEFAULT 'normal'
        );
        INSERT INTO messages (channel_id, agent_id, content) VALUES ('ch1', 'ag1', 'msg1');
    """)
    conn.commit()

    # Verify old schema
    cursor = conn.execute("PRAGMA table_info(messages)")
    cols = {row["name"]: row["type"] for row in cursor.fetchall()}
    assert cols.get("id") == "INTEGER"

    # Run migrations using the new centralized function
    db.migrate(conn, [bridge_db.bridge_migrations[0]])  # Apply only the second migration
    # Verify new schema
    cursor = conn.execute("PRAGMA table_info(messages)")
    cols = {row["name"]: row["type"] for row in cursor.fetchall()}
    assert cols.get("id") == "TEXT"

    # Verify data is preserved and id is now TEXT
    row = conn.execute("SELECT id, content FROM messages").fetchone()
    assert isinstance(row["id"], str)
    assert row["content"] == "msg1"

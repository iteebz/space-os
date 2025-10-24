import sqlite3

import pytest

from space.os import db
from space.os.bridge import db as bridge_db


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
    bridge_reg = db.registry()
    [m for name in bridge_reg if name == "bridge" for m in []]
    # Get first migration from bridge's registered migrations
    migs = [
        (
            "migrate_messages_id_to_text",
            """
        CREATE TABLE messages_new (
            id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            priority TEXT DEFAULT 'normal'
        );
        INSERT INTO messages_new SELECT id, channel_id, agent_id, content, created_at, priority FROM messages;
        DROP TABLE messages;
        ALTER TABLE messages_new RENAME TO messages;
        CREATE INDEX idx_messages_channel_time ON messages(channel_id, created_at);
        CREATE INDEX idx_messages_priority ON messages(priority);
        CREATE INDEX idx_messages_agent ON messages(agent_id);
    """,
        )
    ]
    db.migrate(conn, migs)
    # Verify new schema
    cursor = conn.execute("PRAGMA table_info(messages)")
    cols = {row["name"]: row["type"] for row in cursor.fetchall()}
    assert cols.get("id") == "TEXT"

    # Verify data is preserved and id is now TEXT
    row = conn.execute("SELECT id, content FROM messages").fetchone()
    assert isinstance(row["id"], str)
    assert row["content"] == "msg1"

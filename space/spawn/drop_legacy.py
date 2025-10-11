"""Drop legacy name columns after UUID migration."""

import sqlite3

from ..lib import paths


def drop_columns():
    """Drop old name columns from all tables."""

    print("Creating new tables without legacy columns...")

    dbs = [
        (
            paths.space_root() / "bridge.db",
            "messages",
            """
            CREATE TABLE messages_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                priority TEXT DEFAULT 'normal'
            )
            """,
            "INSERT INTO messages_new SELECT id, channel_id, agent_id, content, created_at, priority FROM messages",
        ),
        (
            paths.space_root() / "memory.db",
            "memory",
            """
            CREATE TABLE memory_new (
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
                code_anchors TEXT
            )
            """,
            "INSERT INTO memory_new SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors FROM memory",
        ),
        (
            paths.space_root() / "knowledge.db",
            "knowledge",
            """
            CREATE TABLE knowledge_new (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archived_at INTEGER
            )
            """,
            "INSERT INTO knowledge_new SELECT id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge",
        ),
        (
            paths.space_root() / "events.db",
            "events",
            """
            CREATE TABLE events_new (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                agent_id TEXT,
                event_type TEXT NOT NULL,
                data TEXT,
                timestamp INTEGER NOT NULL,
                session_id TEXT
            )
            """,
            "INSERT INTO events_new SELECT id, source, agent_id, event_type, data, timestamp, session_id FROM events",
        ),
    ]

    for db_path, table, create_sql, insert_sql in dbs:
        if not db_path.exists():
            continue

        conn = sqlite3.connect(db_path)

        conn.execute(create_sql)
        conn.execute(insert_sql)
        conn.execute(f"DROP TABLE {table}")
        conn.execute(f"ALTER TABLE {table}_new RENAME TO {table}")

        if table == "messages":
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_channel_time ON messages(channel_id, created_at)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_priority ON messages(priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id)")
        elif table == "memory":
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_agent_topic ON memory(agent_id, topic)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_agent_created ON memory(agent_id, created_at)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_uuid ON memory(uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_archived ON memory(archived_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_core ON memory(core)")
        elif table == "knowledge":
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_agent ON knowledge(agent_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_archived ON knowledge(archived_at)"
            )
        elif table == "events":
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON events(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON events(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_id ON events(id)")

        conn.commit()
        conn.close()
        print(f"✓ Dropped legacy columns from {table}")


if __name__ == "__main__":
    drop_columns()

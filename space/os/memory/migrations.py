import contextlib
import sqlite3
import time
import uuid


def _migrate_memory_table_to_memories(conn: sqlite3.Connection):
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory'")
    if not cursor.fetchone():
        return
    cursor = conn.execute("PRAGMA table_info(memory)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "uuid" not in cols or "agent_id" not in cols:
        return
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS memories (
            memory_id TEXT PRIMARY KEY,
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
            synthesis_note TEXT,
            supersedes TEXT,
            superseded_by TEXT
        );
        INSERT OR IGNORE INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note)
            SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note FROM memory;
        DROP TABLE memory;
        CREATE INDEX IF NOT EXISTS idx_memories_agent_topic ON memories(agent_id, topic);
        CREATE INDEX IF NOT EXISTS idx_memories_agent_created ON memories(agent_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_memories_memory_id ON memories(memory_id);
        CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived_at);
        CREATE INDEX IF NOT EXISTS idx_memories_core ON memories(core);
    """
    )
    conn.commit()


def _backfill_memory_links(conn: sqlite3.Connection):
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_links'"
    )
    if not cursor.fetchone():
        return

    now = int(time.time())
    rows = conn.execute(
        "SELECT memory_id, supersedes FROM memories WHERE supersedes IS NOT NULL"
    ).fetchall()
    for row in rows:
        memory_id = row[0]
        supersedes_str = row[1]
        if supersedes_str:
            parent_ids = [pid.strip() for pid in supersedes_str.split(",") if pid.strip()]
            for parent_id in parent_ids:
                link_id = str(uuid.uuid4())
                with contextlib.suppress(sqlite3.IntegrityError):
                    conn.execute(
                        "INSERT OR IGNORE INTO memory_links (link_id, memory_id, parent_id, kind, created_at) VALUES (?, ?, ?, ?, ?)",
                        (link_id, memory_id, parent_id, "supersedes", now),
                    )


MIGRATIONS = [
    ("migrate_memory_table_to_memories", _migrate_memory_table_to_memories),
    ("backfill_memory_links", _backfill_memory_links),
]

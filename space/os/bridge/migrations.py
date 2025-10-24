import sqlite3


def _migrate_bridge_messages_id_to_message_id(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(messages)")
    cols = {row[1] for row in cursor.fetchall()}
    if "id" not in cols:
        return
    conn.executescript(
        """
        CREATE TABLE messages_new (
            message_id TEXT PRIMARY KEY,
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
    """
    )


def _migrate_bridge_channels_id_to_channel_id(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(channels)")
    cols = {row[1] for row in cursor.fetchall()}
    if "channel_id" in cols or "id" not in cols:
        return

    cols_to_select = ["id", "name", "topic", "created_at", "notes", "archived_at"]
    if "pinned_at" in cols:
        cols_to_select.append("pinned_at")
    cols_str = ", ".join(cols_to_select)

    conn.executescript(
        f"""
        DROP TABLE IF EXISTS channels_new;
        CREATE TABLE channels_new (
            channel_id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            topic TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            archived_at TIMESTAMP,
            pinned_at TIMESTAMP
        );
        INSERT INTO channels_new SELECT {cols_str} FROM channels;
        DROP TABLE channels;
        ALTER TABLE channels_new RENAME TO channels;
    """
    )


def _remove_duplicate_channels(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(channels)")
    cols = {row[1] for row in cursor.fetchall()}
    if "channel_id" not in cols:
        return
    conn.execute(
        "DELETE FROM channels WHERE channel_id NOT IN (SELECT MIN(channel_id) FROM channels GROUP BY name)"
    )


MIGRATIONS = [
    ("migrate_bridge_messages_id_to_message_id", _migrate_bridge_messages_id_to_message_id),
    ("migrate_bridge_channels_id_to_channel_id", _migrate_bridge_channels_id_to_channel_id),
    ("remove_duplicate_channels", _remove_duplicate_channels),
    ("drop_bridge_tasks_table", "DROP TABLE IF EXISTS tasks"),
]

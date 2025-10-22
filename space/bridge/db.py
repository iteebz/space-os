import sqlite3
import uuid

from space import db
from space.db import from_row
from space.models import Channel, Export, Message, Note

from ..lib.uuid7 import uuid7

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority TEXT DEFAULT 'normal'
);

CREATE TABLE IF NOT EXISTS bookmarks (
    agent_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    last_seen_id TEXT,
    PRIMARY KEY (agent_id, channel_id)
);

CREATE TABLE IF NOT EXISTS channels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    topic TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    archived_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_time ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_bookmarks ON bookmarks(agent_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_notes ON notes(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_priority ON messages(priority);
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id);
"""

db.register("bridge", "bridge.db", _SCHEMA)

db.add_migrations(
    "bridge",
    [
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
        ),
        (
            "remove_duplicate_channels",
            """
        DELETE FROM channels WHERE id NOT IN (
            SELECT MIN(id) FROM channels GROUP BY name
        );
    """,
        ),
    ],
)


def connect():
    return db.ensure("bridge")


def create_message(channel_id: str, agent_id: str, content: str, priority: str = "normal") -> str:
    message_id = uuid7()
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (id, channel_id, agent_id, content, priority) VALUES (?, ?, ?, ?, ?)",
            (message_id, channel_id, agent_id, content, priority),
        )
        return message_id


def _row_to_message(row: sqlite3.Row) -> Message:
    return from_row(row, Message)


def _row_to_note(row: sqlite3.Row) -> Note:
    return from_row(row, Note)


def get_new_messages(channel_id: str, agent_id: str) -> list[Message]:
    with connect() as conn:
        get_channel_name(channel_id)

        last_seen_id = None
        if agent_id:
            row = conn.execute(
                "SELECT last_seen_id FROM bookmarks WHERE agent_id = ? AND channel_id = ?",
                (agent_id, channel_id),
            ).fetchone()
            last_seen_id = row["last_seen_id"] if row else None

        base_query = """
            SELECT m.id AS message_id, m.channel_id, m.agent_id, m.content, m.created_at
            FROM messages m
            JOIN channels c ON m.channel_id = c.id
            WHERE m.channel_id = ? AND c.archived_at IS NULL
        """

        if last_seen_id is None:
            query = f"{base_query} ORDER BY m.created_at"
            params = (channel_id,)
        else:
            last_seen_row = conn.execute(
                "SELECT created_at, rowid FROM messages WHERE id = ?", (last_seen_id,)
            ).fetchone()
            if last_seen_row:
                query = f"{base_query} AND (m.created_at > ? OR (m.created_at = ? AND m.rowid > ?)) ORDER BY m.created_at, m.rowid"
                params = (
                    channel_id,
                    last_seen_row["created_at"],
                    last_seen_row["created_at"],
                    last_seen_row["rowid"],
                )
            else:
                query = f"{base_query} ORDER BY m.created_at"
                params = (channel_id,)

        cursor = conn.execute(query, params)
        return [_row_to_message(row) for row in cursor.fetchall()]


def get_all_messages(channel_id: str) -> list[Message]:
    with connect() as conn:
        cursor = conn.execute(
            "SELECT id AS message_id, channel_id, agent_id, content, created_at FROM messages WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [_row_to_message(row) for row in cursor.fetchall()]


def set_bookmark(agent_id: str, channel_id: str, last_seen_id: str):
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks (agent_id, channel_id, last_seen_id) VALUES (?, ?, ?)",
            (agent_id, channel_id, last_seen_id),
        )


def get_alerts(agent_id: str) -> list[Message]:
    with connect() as conn:
        cursor = conn.execute(
            """
            SELECT m.id AS message_id, m.channel_id, m.agent_id, m.content, m.created_at
            FROM messages m
            LEFT JOIN bookmarks b ON m.channel_id = b.channel_id AND b.agent_id = ?
            WHERE m.priority = 'alert' AND (b.last_seen_id IS NULL OR m.id > b.last_seen_id)
            ORDER BY m.created_at DESC
            """,
            (agent_id,),
        )
        return [_row_to_message(row) for row in cursor.fetchall()]


def get_sender_history(agent_id: str, limit: int = 5) -> list[Message]:
    with connect() as conn:
        cursor = conn.execute(
            """
            SELECT m.id AS message_id, m.channel_id, m.agent_id, m.content, m.created_at
            FROM messages m
            WHERE m.agent_id = ?
            ORDER BY m.created_at DESC
            LIMIT ?
            """,
            (agent_id, limit),
        )
        return [_row_to_message(row) for row in cursor.fetchall()]


def create_channel(channel_name: str, topic: str | None = None) -> str:
    channel_id = str(uuid.uuid4())
    with connect() as conn:
        conn.execute(
            "INSERT INTO channels (id, name, topic) VALUES (?, ?, ?)",
            (channel_id, channel_name, topic),
        )
    return channel_id


def get_channel_id(channel_name: str) -> str | None:
    with connect() as conn:
        cursor = conn.execute("SELECT id FROM channels WHERE name = ?", (channel_name,))
        result = cursor.fetchone()
        if result:
            return result["id"]

        if len(channel_name) == 8:
            cursor = conn.execute("SELECT id FROM channels WHERE id LIKE ?", (f"%{channel_name}",))
            result = cursor.fetchone()
            if result:
                return result["id"]
    return None


def get_channel_name(channel_id: str) -> str | None:
    with connect() as conn:
        cursor = conn.execute("SELECT name FROM channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()
    return row["name"] if row else None


def set_topic(channel_id: str, topic: str):
    with connect() as conn:
        conn.execute(
            "UPDATE channels SET topic = ? WHERE id = ? AND (topic IS NULL OR topic = '')",
            (topic, channel_id),
        )


def get_topic(channel_id: str) -> str | None:
    with connect() as conn:
        cursor = conn.execute("SELECT topic FROM channels WHERE id = ?", (channel_id,))
        result = cursor.fetchone()
    return result["topic"] if result and result["topic"] else None


def get_participants(channel_id: str) -> list[str]:
    with connect() as conn:
        cursor = conn.execute(
            "SELECT DISTINCT agent_id FROM messages WHERE channel_id = ? ORDER BY agent_id",
            (channel_id,),
        )

        return [row["agent_id"] for row in cursor.fetchall()]


def fetch_channels(
    agent_id: str = None,
    time_filter: str = None,
    include_archived: bool = False,
    unread_only: bool = False,
    active_only: bool = False,
) -> list[Channel]:
    with connect() as conn:
        query = """
            SELECT t.id, t.name, t.topic, t.created_at, t.archived_at,
                   COALESCE(msg_counts.total_messages, 0) as total_messages,
                   msg_counts.last_activity,
                   COALESCE(msg_counts.participants, '') as participants,
                   COALESCE(note_counts.notes_count, 0) as notes_count,
                   COALESCE(unread_counts.unread_count, 0) as unread_count
            FROM channels t
            LEFT JOIN (
                SELECT channel_id, COUNT(*) as total_messages, MAX(created_at) as last_activity,
                       GROUP_CONCAT(DISTINCT agent_id) as participants
                FROM messages
                GROUP BY channel_id
            ) as msg_counts ON t.id = msg_counts.channel_id
            LEFT JOIN (
                SELECT channel_id, COUNT(*) as notes_count
                FROM notes
                GROUP BY channel_id
            ) as note_counts ON t.id = note_counts.channel_id
            LEFT JOIN (
                SELECT m.channel_id, COUNT(m.id) as unread_count
                FROM messages m
                LEFT JOIN bookmarks b ON m.channel_id = b.channel_id AND b.agent_id = ?
                WHERE b.last_seen_id IS NULL OR m.id > b.last_seen_id
                GROUP BY m.channel_id
            ) as unread_counts ON t.id = unread_counts.channel_id
            WHERE 1 = 1
        """
        params = [agent_id]
        if not include_archived:
            query += " AND t.archived_at IS NULL "
        if unread_only:
            query += " AND unread_counts.unread_count > 0 "
        if active_only:
            query += " AND t.archived_at IS NULL "  # Ensure active_only implies not archived

        if time_filter:
            query += " AND t.created_at > datetime('now', ?) "
            params.append(time_filter)

        query += " ORDER BY t.created_at DESC"
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        channels = []
        for row in rows:
            participants_list = row["participants"].split(",") if row["participants"] else []
            channels.append(
                Channel(
                    channel_id=row["id"],
                    name=row["name"],
                    topic=row["topic"],
                    created_at=row["created_at"],
                    archived_at=row["archived_at"],
                    participants=participants_list,
                    message_count=row["total_messages"],
                    last_activity=row["last_activity"],
                    unread_count=row["unread_count"],
                    notes_count=row["notes_count"],
                )
            )
    return channels


def get_export_data(channel_id: str) -> Export:
    with connect() as conn:
        channel_cursor = conn.execute(
            "SELECT name, topic, created_at FROM channels WHERE id = ?", (channel_id,)
        )
        channel_info = channel_cursor.fetchone()

        msg_cursor = conn.execute(
            "SELECT id AS message_id, channel_id, agent_id, content, created_at FROM messages WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        messages = [_row_to_message(row) for row in msg_cursor.fetchall()]

        note_cursor = conn.execute(
            "SELECT note_id, agent_id, content, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        notes = [_row_to_note(row) for row in note_cursor.fetchall()]

    participants = sorted({msg.agent_id for msg in messages})

    return Export(
        channel_id=channel_id,
        channel_name=channel_info["name"] if channel_info else None,
        topic=channel_info["topic"] if channel_info else None,
        created_at=channel_info["created_at"] if channel_info else None,
        participants=participants,
        message_count=len(messages),
        messages=messages,
        notes=notes,
    )


def archive_channel(channel_id: str):
    with connect() as conn:
        conn.execute(
            "UPDATE channels SET archived_at = CURRENT_TIMESTAMP WHERE id = ?",
            (channel_id,),
        )


def delete_channel(channel_id: str):
    with connect() as conn:
        conn.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM bookmarks WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))


def rename_channel(old_name: str, new_name: str) -> bool:
    with connect() as conn:
        try:
            conn.execute("UPDATE channels SET name = ? WHERE name = ?", (new_name, old_name))
            return True
        except sqlite3.IntegrityError:
            return False


def create_note(channel_id: str, agent_id: str, content: str) -> str:
    note_id = uuid7()
    with connect() as conn:
        conn.execute(
            "INSERT INTO notes (note_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            (note_id, channel_id, agent_id, content),
        )
    return note_id


def get_notes(channel_id: str) -> list[Note]:
    with connect() as conn:
        cursor = conn.execute(
            "SELECT note_id, agent_id, content, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [from_row(row, Note) for row in cursor.fetchall()]

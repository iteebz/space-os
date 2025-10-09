import sqlite3
from pathlib import Path

from ..errors import ChannelNotFoundError
from ..lib import db as libdb
from ..lib.ids import uuid7
from .models import Channel, ExportData, Message, Note

BRIDGE_DB_NAME = "bridge.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority TEXT DEFAULT 'normal'
);

CREATE TABLE IF NOT EXISTS bookmarks (
    agent_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    last_seen_id INTEGER DEFAULT 0,
    PRIMARY KEY (agent_id, channel_id)
);

CREATE TABLE IF NOT EXISTS channels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    topic TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    archived_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_time ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_bookmarks ON bookmarks(agent_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_notes ON notes(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_priority ON messages(priority);
"""


def _path() -> Path:
    return libdb.workspace_db_path(libdb.workspace_root(), BRIDGE_DB_NAME)


def _connect():
    return libdb.workspace_db(libdb.workspace_root(), BRIDGE_DB_NAME, _SCHEMA)


def create_message(channel_id: str, sender: str, content: str, priority: str = "normal") -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (channel_id, sender, content, priority) VALUES (?, ?, ?, ?)",
            (channel_id, sender, content, priority),
        )
        conn.commit()
        return cursor.lastrowid


def get_new_messages(channel_id: str, agent_id: str | None = None) -> list[Message]:
    with _connect() as conn:
        last_seen_id = None
        if agent_id:
            row = conn.execute(
                "SELECT last_seen_id FROM bookmarks WHERE agent_id = ? AND channel_id = ?",
                (agent_id, channel_id),
            ).fetchone()
            last_seen_id = row["last_seen_id"] if row else None

        base_query = """
            SELECT m.id, m.channel_id, m.sender, m.content, m.created_at
            FROM messages m
            JOIN channels c ON m.channel_id = c.id
            WHERE m.channel_id = ? AND c.archived_at IS NULL
        """

        if last_seen_id is None:
            query = f"{base_query} ORDER BY m.id"
            params = (channel_id,)
        else:
            query = f"{base_query} AND m.id > ? ORDER BY m.id"
            params = (channel_id, last_seen_id)

        cursor = conn.execute(query, params)
        return [Message(*row) for row in cursor.fetchall()]


def get_all_messages(channel_id: str) -> list[Message]:
    with _connect() as conn:
        cursor = conn.execute(
            "SELECT id, channel_id, sender, content, created_at FROM messages WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [Message(**row) for row in cursor.fetchall()]


def get_sender_history(sender: str, limit: int | None = None) -> list[Message]:
    with _connect() as conn:
        query = "SELECT id, channel_id, sender, content, created_at FROM messages WHERE sender = ? ORDER BY created_at DESC"
        params = (sender, limit) if limit else (sender,)
        if limit:
            query += " LIMIT ?"
        return [Message(**row) for row in conn.execute(query, params).fetchall()]


def set_bookmark(agent_id: str, channel_id: str, last_seen_id: int):
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks (agent_id, channel_id, last_seen_id) VALUES (?, ?, ?)",
            (agent_id, channel_id, last_seen_id),
        )
        conn.commit()


def get_alerts(agent_id: str) -> list[Message]:
    with _connect() as conn:
        cursor = conn.execute(
            """
            SELECT m.id, m.channel_id, m.sender, m.content, m.created_at
            FROM messages m
            LEFT JOIN bookmarks b ON m.channel_id = b.channel_id AND b.agent_id = ?
            WHERE m.priority = 'alert' AND (b.last_seen_id IS NULL OR m.id > b.last_seen_id)
            ORDER BY m.created_at DESC
            """,
            (agent_id,),
        )
        return [Message(**row) for row in cursor.fetchall()]


def create_channel(channel_name: str, topic: str | None = None) -> str:
    channel_id = uuid7()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO channels (id, name, topic) VALUES (?, ?, ?)",
            (channel_id, channel_name, topic),
        )
        conn.commit()
    return channel_id


def get_channel_id(channel_name: str) -> str:
    with _connect() as conn:
        cursor = conn.execute("SELECT id FROM channels WHERE name = ?", (channel_name,))
        result = cursor.fetchone()
    if not result:
        raise ChannelNotFoundError(f"Channel '{channel_name}' not found")
    return result["id"]


def get_channel_name(channel_id: str) -> str | None:
    with _connect() as conn:
        cursor = conn.execute("SELECT name FROM channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()
    return row["name"] if row else None


def set_topic(channel_id: str, topic: str):
    with _connect() as conn:
        conn.execute(
            "UPDATE channels SET topic = ? WHERE id = ? AND (topic IS NULL OR topic = '')",
            (topic, channel_id),
        )
        conn.commit()


def get_topic(channel_id: str) -> str | None:
    with _connect() as conn:
        cursor = conn.execute("SELECT topic FROM channels WHERE id = ?", (channel_id,))
        result = cursor.fetchone()
    return result["topic"] if result and result["topic"] else None


def get_participants(channel_id: str) -> list[str]:
    with _connect() as conn:
        cursor = conn.execute(
            "SELECT DISTINCT sender FROM messages WHERE channel_id = ? ORDER BY sender",
            (channel_id,),
        )
        return [row["sender"] for row in cursor.fetchall()]


def fetch_channels(agent_id: str = None, time_filter: str = None) -> list[Channel]:
    with _connect() as conn:
        query = """
            SELECT t.id, t.name, t.topic, t.created_at,
                   COALESCE(msg_counts.total_messages, 0) as total_messages,
                   msg_counts.last_activity,
                   COALESCE(msg_counts.participants, '') as participants,
                   COALESCE(note_counts.notes_count, 0) as notes_count
            FROM channels t
            LEFT JOIN (
                SELECT channel_id, COUNT(id) as total_messages, MAX(created_at) as last_activity,
                       GROUP_CONCAT(DISTINCT sender) as participants
                FROM messages
                GROUP BY channel_id
            ) as msg_counts ON t.id = msg_counts.channel_id
            LEFT JOIN (
                SELECT channel_id, COUNT(id) as notes_count
                FROM notes
                GROUP BY channel_id
            ) as note_counts ON t.id = note_counts.channel_id
        """
        params = []
        if time_filter:
            query += " WHERE t.created_at > datetime('now', ?) "
            params.append(time_filter)

        query += " ORDER BY t.created_at DESC"
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        channels = []
        for row in rows:
            participants_list = row["participants"].split(",") if row["participants"] else []
            unread_count = 0
            if agent_id:
                cursor2 = conn.execute(
                    """
                    SELECT COUNT(*) as count FROM messages m
                    LEFT JOIN bookmarks b ON b.channel_id = m.channel_id AND b.agent_id = ?
                    WHERE m.channel_id = ? AND m.id > COALESCE(b.last_seen_id, 0)
                    """,
                    (agent_id, row["id"]),
                )
                unread_count = cursor2.fetchone()["count"]

            channels.append(
                Channel(
                    name=row["name"],
                    topic=row["topic"],
                    created_at=row["created_at"],
                    participants=participants_list,
                    message_count=row["total_messages"],
                    last_activity=row["last_activity"],
                    unread_count=unread_count,
                    notes_count=row["notes_count"],
                )
            )
    return channels


def get_export_data(channel_id: str) -> ExportData:
    with _connect() as conn:
        channel_cursor = conn.execute(
            "SELECT name, topic, created_at FROM channels WHERE id = ?", (channel_id,)
        )
        channel_info = channel_cursor.fetchone()

        msg_cursor = conn.execute(
            "SELECT id, channel_id, sender, content, created_at FROM messages WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        messages = [Message(**row) for row in msg_cursor.fetchall()]

        note_cursor = conn.execute(
            "SELECT author, content, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        notes = [Note(**row) for row in note_cursor.fetchall()]

    participants = sorted({msg.sender for msg in messages})

    return ExportData(
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
    with _connect() as conn:
        conn.execute(
            "UPDATE channels SET archived_at = CURRENT_TIMESTAMP WHERE id = ?",
            (channel_id,),
        )
        conn.commit()


def delete_channel(channel_id: str):
    with _connect() as conn:
        conn.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM bookmarks WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        conn.commit()


def create_note(channel_id: str, author: str, content: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO notes (channel_id, author, content) VALUES (?, ?, ?)",
            (channel_id, author, content),
        )
        conn.commit()
        return cursor.lastrowid


def get_notes(channel_id: str) -> list[Note]:
    with _connect() as conn:
        cursor = conn.execute(
            "SELECT author, content, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [Note(**row) for row in cursor.fetchall()]

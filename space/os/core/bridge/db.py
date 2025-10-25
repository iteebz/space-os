import sqlite3
import uuid
from pathlib import Path

from space.os import db
from space.os.db import from_row
from space.os.db import query_builders as qb
from space.os.lib import paths
from space.os.lib.uuid7 import uuid7
from space.os.models import BridgeMessage, Channel, Export, Note

from . import migrations


def schema() -> str:
    """Bridge database schema."""
    return """
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
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
    channel_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    topic TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    archived_at TIMESTAMP,
    pinned_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
);

CREATE TABLE IF NOT EXISTS polls (
    poll_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    poll_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    poll_dismissed_at TIMESTAMP,
    created_by TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_time ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_bookmarks ON bookmarks(agent_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_notes ON notes(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_priority ON messages(priority);
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id);
CREATE INDEX IF NOT EXISTS idx_polls_active ON polls(agent_id, channel_id, poll_dismissed_at);
"""


db.register("bridge", "bridge.db", schema())
db.add_migrations("bridge", migrations.MIGRATIONS)


def path() -> Path:
    return paths.space_data() / "bridge.db"


def connect():
    return db.ensure("bridge")


def create_message(channel_id: str, agent_id: str, content: str, priority: str = "normal") -> str:
    message_id = uuid7()
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content, priority) VALUES (?, ?, ?, ?, ?)",
            (message_id, channel_id, agent_id, content, priority),
        )
        return message_id


def _row_to_message(row: sqlite3.Row) -> BridgeMessage:
    return from_row(row, BridgeMessage)


def _row_to_note(row: sqlite3.Row) -> Note:
    return from_row(row, Note)


def get_new_messages(channel_id: str, agent_id: str) -> list[BridgeMessage]:
    with db.ensure("bridge") as conn:
        get_channel_name(channel_id)

        last_seen_id = None
        if agent_id:
            row = conn.execute(
                "SELECT last_seen_id FROM bookmarks WHERE agent_id = ? AND channel_id = ?",
                (agent_id, channel_id),
            ).fetchone()
            last_seen_id = row["last_seen_id"] if row else None

        base_query = """
            SELECT m.message_id, m.channel_id, m.agent_id, m.content, m.created_at
            FROM messages m
            JOIN channels c ON m.channel_id = c.channel_id
            WHERE m.channel_id = ? AND c.archived_at IS NULL
        """

        if last_seen_id is None:
            query = f"{base_query} ORDER BY m.created_at"
            params = (channel_id,)
        else:
            last_seen_row = conn.execute(
                "SELECT created_at, rowid FROM messages WHERE message_id = ?", (last_seen_id,)
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


def get_all_messages(channel_id: str) -> list[BridgeMessage]:
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            "SELECT message_id, channel_id, agent_id, content, created_at FROM messages WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [_row_to_message(row) for row in cursor.fetchall()]


def set_bookmark(agent_id: str, channel_id: str, last_seen_id: str) -> None:
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks (agent_id, channel_id, last_seen_id) VALUES (?, ?, ?)",
            (agent_id, channel_id, last_seen_id),
        )


def get_alerts(agent_id: str) -> list[BridgeMessage]:
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            """
            SELECT m.message_id, m.channel_id, m.agent_id, m.content, m.created_at
            FROM messages m
            LEFT JOIN bookmarks b ON m.channel_id = b.channel_id AND b.agent_id = ?
            WHERE m.priority = 'alert' AND (b.last_seen_id IS NULL OR m.message_id > b.last_seen_id)
            ORDER BY m.created_at DESC
            """,
            (agent_id,),
        )
        return [_row_to_message(row) for row in cursor.fetchall()]


def get_sender_history(agent_id: str, limit: int = 5) -> list[BridgeMessage]:
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            """
            SELECT m.message_id, m.channel_id, m.agent_id, m.content, m.created_at
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
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO channels (channel_id, name, topic) VALUES (?, ?, ?)",
            (channel_id, channel_name, topic),
        )
    return channel_id


def get_channel_id(channel_name: str) -> str | None:
    with db.ensure("bridge") as conn:
        cursor = conn.execute("SELECT channel_id FROM channels WHERE name = ?", (channel_name,))
        result = cursor.fetchone()
        if result:
            return result["channel_id"]

        if len(channel_name) == 8:
            cursor = conn.execute(
                "SELECT channel_id FROM channels WHERE channel_id LIKE ?", (f"%{channel_name}",)
            )
            result = cursor.fetchone()
            if result:
                return result["channel_id"]
    return None


def get_channel_name(channel_id: str) -> str | None:
    with db.ensure("bridge") as conn:
        cursor = conn.execute("SELECT name FROM channels WHERE channel_id = ?", (channel_id,))
        row = cursor.fetchone()
    return row["name"] if row else None


def set_topic(channel_id: str, topic: str) -> None:
    with db.ensure("bridge") as conn:
        conn.execute(
            "UPDATE channels SET topic = ? WHERE channel_id = ? AND (topic IS NULL OR topic = '')",
            (topic, channel_id),
        )


def get_topic(channel_id: str) -> str | None:
    with db.ensure("bridge") as conn:
        cursor = conn.execute("SELECT topic FROM channels WHERE channel_id = ?", (channel_id,))
        result = cursor.fetchone()
    return result["topic"] if result and result["topic"] else None


def get_participants(channel_id: str) -> list[str]:
    with db.ensure("bridge") as conn:
        return qb.select_distinct(
            conn,
            "messages",
            "agent_id",
            where="channel_id = ?",
            params=(channel_id,),
            include_archived=True,
        )


def fetch_channels(
    agent_id: str = None,
    time_filter: str = None,
    include_archived: bool = False,
    unread_only: bool = False,
    active_only: bool = False,
) -> list[Channel]:
    with db.ensure("bridge") as conn:
        query = """
            SELECT t.channel_id AS id, t.name, t.topic, t.created_at, t.archived_at,
                   COALESCE(msg_counts.total_messages, 0) as total_messages,
                   msg_counts.last_activity,
                   COALESCE(msg_counts.participants, '') as participants,
                   COALESCE(note_counts.notes_count, 0) as notes_count
            FROM channels t
            LEFT JOIN (
                SELECT channel_id, COUNT(*) as total_messages, MAX(created_at) as last_activity,
                       GROUP_CONCAT(DISTINCT agent_id) as participants
                FROM messages
                GROUP BY channel_id
            ) as msg_counts ON t.channel_id = msg_counts.channel_id
            LEFT JOIN (
                SELECT channel_id, COUNT(*) as notes_count
                FROM notes
                GROUP BY channel_id
            ) as note_counts ON t.channel_id = note_counts.channel_id
        """

        params = []

        if agent_id:
            query += """
            LEFT JOIN (
                SELECT m.channel_id, COUNT(m.message_id) as unread_count
                FROM messages m
                LEFT JOIN bookmarks b ON m.channel_id = b.channel_id AND b.agent_id = ?
                WHERE (b.agent_id IS NULL OR m.message_id > b.last_seen_id)
                GROUP BY m.channel_id
            ) as unread_counts ON t.channel_id = unread_counts.channel_id
            """
            params.append(agent_id)

        query += " WHERE 1 = 1"

        if not include_archived:
            query += " AND t.archived_at IS NULL"
        if unread_only and agent_id:
            query += " AND unread_counts.unread_count > 0"
        if active_only:
            query += " AND t.archived_at IS NULL"

        if time_filter:
            query += " AND t.created_at > datetime('now', ?)"
            params.append(time_filter)

        query += " ORDER BY t.created_at DESC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        channels = []
        for row in rows:
            participants_list = row["participants"].split(",") if row["participants"] else []
            unread_count = 0
            if agent_id:
                try:
                    unread_count = row["unread_count"]
                except (KeyError, IndexError):
                    unread_count = 0
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
                    unread_count=unread_count,
                    notes_count=row["notes_count"],
                )
            )
    return channels


def get_export_data(channel_id: str) -> Export:
    with db.ensure("bridge") as conn:
        channel_cursor = conn.execute(
            "SELECT name, topic, created_at FROM channels WHERE channel_id = ?", (channel_id,)
        )
        channel_info = channel_cursor.fetchone()

        msg_cursor = conn.execute(
            "SELECT message_id, channel_id, agent_id, content, created_at FROM messages WHERE channel_id = ? ORDER BY created_at ASC",
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


def rename_channel(old_name: str, new_name: str) -> bool:
    with db.ensure("bridge") as conn:
        try:
            conn.execute("UPDATE channels SET name = ? WHERE name = ?", (new_name, old_name))
            return True
        except sqlite3.IntegrityError:
            return False


def create_note(channel_id: str, agent_id: str, content: str) -> str:
    note_id = uuid7()
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO notes (note_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            (note_id, channel_id, agent_id, content),
        )
    return note_id


def get_notes(channel_id: str) -> list[Note]:
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            "SELECT note_id, agent_id, content, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [from_row(row, Note) for row in cursor.fetchall()]


def send_message(channel_id: str, identity: str, content: str, priority: str = "normal") -> str:
    """Send message and return agent_id."""
    from .. import spawn

    if not identity:
        raise ValueError("identity is required")
    if not channel_id:
        raise ValueError("channel_id is required")

    agent_id = spawn.db.ensure_agent(identity)
    create_message(channel_id, agent_id, content, priority)
    return agent_id


def spawn_agents_from_mentions(channel_id: str, content: str) -> None:
    """Spawn agents from @mentions in content."""
    import subprocess
    import sys

    from .. import spawn

    if "@" not in content:
        return

    channel_name = get_channel_name(channel_id)
    system_id = spawn.db.ensure_agent("system")
    create_message(channel_id, system_id, "spawning agent(s)", "normal")

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "space.os.core.bridge.worker",
            channel_id,
            channel_name,
            content,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def resolve_channel_id(channel_name: str) -> str:
    """Resolve channel name to UUID, creating channel if needed."""
    channel_id = get_channel_id(channel_name)
    if channel_id is None:
        channel_id = create_channel(channel_name)
    return channel_id


def recv_updates(channel_id: str, identity: str) -> tuple[list[BridgeMessage], int, str, list[str]]:
    """Receive topic updates, returning messages, count, context, and participants."""
    from .. import spawn

    channel_name = get_channel_name(channel_id)
    agent_id = spawn.db.ensure_agent(identity)

    messages = get_new_messages(channel_id, agent_id)

    if channel_name == "summary" and messages:
        messages = [messages[-1]]

    unread_count = len(messages)

    if messages:
        set_bookmark(agent_id, channel_id, messages[-1].message_id)

    topic = get_topic(channel_id)
    participants = get_participants(channel_id)
    return messages, unread_count, topic, participants


def inbox_channels(identity: str = None, agent_id: str = None, limit: int = 5) -> list[Channel]:
    """Get all channels with unreads."""
    from .. import spawn

    if agent_id is None and identity is None:
        raise ValueError("Must provide either identity or agent_id")

    resolved_id = agent_id or identity
    if resolved_id:
        resolved_id = spawn.db.ensure_agent(resolved_id)

    channels = fetch_channels(resolved_id, unread_only=True, active_only=True)
    channels.sort(key=lambda t: t.last_activity if t.last_activity else "", reverse=True)
    return channels


def all_channels(include_archived: bool = False) -> list[Channel]:
    """Get all channels."""
    return fetch_channels(include_archived=include_archived)


def archive_channel(channel_name: str) -> None:
    """Archive channel by name."""
    channel_id = get_channel_id(channel_name)
    if not channel_id:
        raise ValueError(f"Channel '{channel_name}' not found")
    with db.ensure("bridge") as conn:
        conn.execute(
            "UPDATE channels SET archived_at = CURRENT_TIMESTAMP WHERE channel_id = ?",
            (channel_id,),
        )


def pin_channel(channel_name: str) -> None:
    """Pin channel by name."""
    channel_id = get_channel_id(channel_name)
    if not channel_id:
        raise ValueError(f"Channel '{channel_name}' not found")
    with db.ensure("bridge") as conn:
        conn.execute(
            "UPDATE channels SET pinned_at = CURRENT_TIMESTAMP WHERE channel_id = ?",
            (channel_id,),
        )


def unpin_channel(channel_name: str) -> None:
    """Unpin channel by name."""
    channel_id = get_channel_id(channel_name)
    if not channel_id:
        raise ValueError(f"Channel '{channel_name}' not found")
    with db.ensure("bridge") as conn:
        conn.execute(
            "UPDATE channels SET pinned_at = NULL WHERE channel_id = ?",
            (channel_id,),
        )


def delete_channel(channel_name: str) -> None:
    """Delete channel by name."""
    channel_id = get_channel_id(channel_name)
    if not channel_id:
        raise ValueError(f"Channel '{channel_name}' not found")
    with db.ensure("bridge") as conn:
        conn.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM bookmarks WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))


def add_note(channel_id: str, identity: str, content: str) -> str:
    """Add note, handling identity → agent_id resolution."""
    from .. import spawn

    agent_id = spawn.db.ensure_agent(identity)
    return create_note(channel_id, agent_id, content)


def active_channels(agent_id: str = None, limit: int = 5) -> list[Channel]:
    """Get active channels with unreads, limited to most recent."""
    from .. import spawn

    if not agent_id:
        raise ValueError("agent_id is required")

    resolved_id = spawn.db.ensure_agent(agent_id)

    channels = fetch_channels(
        resolved_id, time_filter="-7 days", unread_only=True, active_only=True
    )
    channels.sort(key=lambda t: t.last_activity if t.last_activity else "", reverse=True)
    return channels[:limit]


def fetch_agent_history(identity: str, limit: int = 5) -> list[BridgeMessage]:
    """Retrieve message history for a given agent identity."""
    from .. import spawn

    agent_id = spawn.db.ensure_agent(identity)
    return get_sender_history(agent_id, limit)


def get_channel_topic(channel_id: str) -> str | None:
    """Get the topic for a specific channel."""
    return get_topic(channel_id)


def fetch_messages(channel_id: str) -> list[BridgeMessage]:
    """Alias for get_all_messages."""
    return get_all_messages(channel_id)


def create_poll(agent_id: str, channel_id: str, created_by: str = "human") -> str:
    """Create a poll record. Returns poll_id."""
    poll_id = uuid.uuid4().hex
    with db.ensure("bridge") as conn:
        conn.execute(
            """
            INSERT INTO polls (poll_id, agent_id, channel_id, created_by)
            VALUES (?, ?, ?, ?)
            """,
            (poll_id, agent_id, channel_id, created_by),
        )
    return poll_id


def dismiss_poll(agent_id: str, channel_id: str) -> bool:
    """Dismiss active poll for agent in channel. Returns True if dismissed."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            """
            UPDATE polls SET poll_dismissed_at = CURRENT_TIMESTAMP
            WHERE agent_id = ? AND channel_id = ? AND poll_dismissed_at IS NULL
            """,
            (agent_id, channel_id),
        )
        return cursor.rowcount > 0


def get_active_polls(channel_id: str | None = None) -> list[dict]:
    """Get active polls (not dismissed)."""
    with db.ensure("bridge") as conn:
        if channel_id:
            cursor = conn.execute(
                """
                SELECT p.poll_id, p.agent_id, p.channel_id, p.poll_started_at
                FROM polls p
                WHERE p.channel_id = ? AND p.poll_dismissed_at IS NULL
                ORDER BY p.poll_started_at DESC
                """,
                (channel_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT p.poll_id, p.agent_id, p.channel_id, p.poll_started_at
                FROM polls p
                WHERE p.poll_dismissed_at IS NULL
                ORDER BY p.poll_started_at DESC
                """
            )
        return [dict(row) for row in cursor.fetchall()]


def is_polling(agent_id: str, channel_id: str) -> bool:
    """Check if agent has active poll in channel."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            """
            SELECT COUNT(*) as count FROM polls
            WHERE agent_id = ? AND channel_id = ? AND poll_dismissed_at IS NULL
            """,
            (agent_id, channel_id),
        )
        row = cursor.fetchone()
        return row["count"] > 0 if row else False

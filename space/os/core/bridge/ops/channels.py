"""Channel operations: create, rename, archive, pin, list, resolve."""

import sqlite3
import uuid

from space.os import db
from space.os.db import from_row
from space.os.models import Channel


def _row_to_channel(row: sqlite3.Row) -> Channel:
    return from_row(row, Channel)


def create_channel(name: str, topic: str | None = None) -> str:
    """Create channel. Returns channel_id."""
    if not name:
        raise ValueError("Channel name is required")

    channel_id = uuid.uuid4().hex
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO channels (channel_id, name, topic) VALUES (?, ?, ?)",
            (channel_id, name, topic),
        )
    return channel_id


def get_channel_id(name: str) -> str | None:
    """Get channel ID by name. Returns None if not found."""
    with db.ensure("bridge") as conn:
        row = conn.execute(
            "SELECT channel_id FROM channels WHERE name = ?",
            (name,),
        ).fetchone()
        return row["channel_id"] if row else None


def get_channel_name(channel_id: str) -> str:
    """Get channel name by ID. Raises ValueError if not found."""
    with db.ensure("bridge") as conn:
        row = conn.execute(
            "SELECT name FROM channels WHERE channel_id = ?",
            (channel_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Channel {channel_id} not found")
        return row["name"]


def resolve_channel_id(name: str) -> str:
    """Resolve channel name to ID. Creates if not exists. Returns channel_id."""
    channel_id = get_channel_id(name)
    if channel_id:
        return channel_id
    return create_channel(name)


def rename_channel(old_name: str, new_name: str) -> bool:
    """Rename channel. Returns True if successful."""
    with db.ensure("bridge") as conn:
        row = conn.execute(
            "SELECT channel_id FROM channels WHERE name = ?",
            (old_name,),
        ).fetchone()
        if not row:
            return False

        try:
            conn.execute(
                "UPDATE channels SET name = ? WHERE channel_id = ?",
                (new_name, row["channel_id"]),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def archive_channel(name: str) -> None:
    """Archive channel by setting archived_at. Raises ValueError if not found."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            "UPDATE channels SET archived_at = CURRENT_TIMESTAMP WHERE name = ? AND archived_at IS NULL",
            (name,),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Channel '{name}' not found or already archived")


def pin_channel(name: str) -> None:
    """Pin channel. Raises ValueError if not found."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            "UPDATE channels SET pinned_at = CURRENT_TIMESTAMP WHERE name = ? AND pinned_at IS NULL",
            (name,),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Channel '{name}' not found or already pinned")


def unpin_channel(name: str) -> None:
    """Unpin channel. Raises ValueError if not found."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            "UPDATE channels SET pinned_at = NULL WHERE name = ? AND pinned_at IS NOT NULL",
            (name,),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Channel '{name}' not found or not pinned")


def delete_channel(name: str) -> None:
    """Hard delete channel and all messages/bookmarks. Raises ValueError if not found."""
    with db.ensure("bridge") as conn:
        row = conn.execute(
            "SELECT channel_id FROM channels WHERE name = ?",
            (name,),
        ).fetchone()
        if not row:
            raise ValueError(f"Channel '{name}' not found")

        channel_id = row["channel_id"]
        conn.execute("DELETE FROM bookmarks WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM notes WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM polls WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))


def all_channels(include_archived: bool = False) -> list[Channel]:
    """Get all channels with metadata."""
    with db.ensure("bridge") as conn:
        archived_clause = "" if include_archived else "AND c.archived_at IS NULL"
        query = f"""
            SELECT
                c.channel_id,
                c.name,
                c.topic,
                c.created_at,
                c.archived_at,
                COUNT(DISTINCT m.agent_id) as participants_count,
                COUNT(m.message_id) as message_count,
                MAX(m.created_at) as last_activity,
                COUNT(n.note_id) as notes_count,
                0 as unread_count
            FROM channels c
            LEFT JOIN messages m ON c.channel_id = m.channel_id
            LEFT JOIN notes n ON c.channel_id = n.channel_id
            WHERE 1=1 {archived_clause}
            GROUP BY c.channel_id
            ORDER BY COALESCE(MAX(m.created_at), c.created_at) DESC
        """
        cursor = conn.execute(query)
        return [_row_to_channel(row) for row in cursor.fetchall()]


def active_channels(agent_id: str) -> list[Channel]:
    """Get up to 5 channels with unread messages for agent, ordered by recency."""
    with db.ensure("bridge") as conn:
        query = """
            WITH last_seen AS (
                SELECT b.channel_id, m.created_at, m.rowid
                FROM bookmarks b
                JOIN messages m ON m.message_id = b.last_seen_id
                WHERE b.agent_id = ?
            )
            SELECT
                c.channel_id,
                c.name,
                c.topic,
                c.created_at,
                c.archived_at,
                COUNT(DISTINCT m.agent_id) as participants_count,
                COUNT(m.message_id) as message_count,
                MAX(m.created_at) as last_activity,
                COUNT(n.note_id) as notes_count,
                SUM(CASE
                    WHEN ls.channel_id IS NULL THEN 1
                    WHEN m.created_at > ls.created_at OR (m.created_at = ls.created_at AND m.rowid > ls.rowid) THEN 1
                    ELSE 0
                END) as unread_count
            FROM channels c
            LEFT JOIN messages m ON c.channel_id = m.channel_id
            LEFT JOIN last_seen ls ON c.channel_id = ls.channel_id
            LEFT JOIN notes n ON c.channel_id = n.channel_id
            WHERE c.archived_at IS NULL
            GROUP BY c.channel_id
            HAVING unread_count > 0
            ORDER BY MAX(m.created_at) DESC
            LIMIT 5
        """
        cursor = conn.execute(query, (agent_id,))
        return [_row_to_channel(row) for row in cursor.fetchall()]


def inbox_channels(agent_id: str) -> list[Channel]:
    """Get all channels with unread messages for agent."""
    with db.ensure("bridge") as conn:
        query = """
            WITH last_seen AS (
                SELECT b.channel_id, m.created_at, m.rowid
                FROM bookmarks b
                JOIN messages m ON m.message_id = b.last_seen_id
                WHERE b.agent_id = ?
            )
            SELECT
                c.channel_id,
                c.name,
                c.topic,
                c.created_at,
                c.archived_at,
                COUNT(DISTINCT m.agent_id) as participants_count,
                COUNT(m.message_id) as message_count,
                MAX(m.created_at) as last_activity,
                COUNT(n.note_id) as notes_count,
                SUM(CASE
                    WHEN ls.channel_id IS NULL THEN 1
                    WHEN m.created_at > ls.created_at OR (m.created_at = ls.created_at AND m.rowid > ls.rowid) THEN 1
                    ELSE 0
                END) as unread_count
            FROM channels c
            LEFT JOIN messages m ON c.channel_id = m.channel_id
            LEFT JOIN last_seen ls ON c.channel_id = ls.channel_id
            LEFT JOIN notes n ON c.channel_id = n.channel_id
            WHERE c.archived_at IS NULL
            GROUP BY c.channel_id
            HAVING unread_count > 0
            ORDER BY MAX(m.created_at) DESC
        """
        cursor = conn.execute(query, (agent_id,))
        return [_row_to_channel(row) for row in cursor.fetchall()]


def get_topic(channel_id: str) -> str | None:
    """Get channel topic."""
    with db.ensure("bridge") as conn:
        row = conn.execute(
            "SELECT topic FROM channels WHERE channel_id = ?",
            (channel_id,),
        ).fetchone()
        return row["topic"] if row else None


def get_participants(channel_id: str) -> list[str]:
    """Get unique agent IDs that have posted in channel."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            "SELECT DISTINCT agent_id FROM messages WHERE channel_id = ? ORDER BY agent_id",
            (channel_id,),
        )
        return [row["agent_id"] for row in cursor.fetchall()]

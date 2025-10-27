"""Channel operations: create, rename, archive, pin, list, resolve."""

import sqlite3
import uuid

from space.core.models import Channel, Export
from space.lib import store
from space.lib.store import from_row

from . import messaging, notes


def _row_to_channel(row: store.Row) -> Channel:
    return from_row(row, Channel)


def _to_channel_id(channel: str | Channel) -> str:
    """Extract channel_id from Channel object or return string as-is."""
    return channel.channel_id if isinstance(channel, Channel) else channel


def create_channel(name: str, topic: str | None = None) -> Channel:
    """Create channel. Returns Channel object."""
    if not name:
        raise ValueError("Channel name is required")

    channel_id = uuid.uuid4().hex
    with store.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO channels (channel_id, name, topic) VALUES (?, ?, ?)",
            (channel_id, name, topic),
        )
    return Channel(channel_id=channel_id, name=name, topic=topic)


def resolve_channel(identifier: str) -> Channel:
    """Resolve channel by name or ID. Creates if not exists. Returns Channel object."""
    with store.ensure("bridge") as conn:
        row = conn.execute(
            "SELECT channel_id, name, topic, created_at, archived_at FROM channels WHERE name = ? OR channel_id = ? LIMIT 1",
            (identifier, identifier),
        ).fetchone()

        if row:
            channel = _row_to_channel(row)
            channel.members = [
                p_row["agent_id"]
                for p_row in conn.execute(
                    "SELECT DISTINCT agent_id FROM messages WHERE channel_id = ? ORDER BY agent_id",
                    (channel.channel_id,),
                ).fetchall()
            ]
            return channel

    return create_channel(identifier)


def rename_channel(old_name: str, new_name: str) -> bool:
    """Rename channel. Returns True if successful."""
    with store.ensure("bridge") as conn:
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
    with store.ensure("bridge") as conn:
        cursor = conn.execute(
            "UPDATE channels SET archived_at = CURRENT_TIMESTAMP WHERE name = ? AND archived_at IS NULL",
            (name,),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Channel '{name}' not found or already archived")


def pin_channel(name: str) -> None:
    """Pin channel. Raises ValueError if not found."""
    with store.ensure("bridge") as conn:
        cursor = conn.execute(
            "UPDATE channels SET pinned_at = CURRENT_TIMESTAMP WHERE name = ? AND pinned_at IS NULL",
            (name,),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Channel '{name}' not found or already pinned")


def unpin_channel(name: str) -> None:
    """Unpin channel. Raises ValueError if not found."""
    with store.ensure("bridge") as conn:
        cursor = conn.execute(
            "UPDATE channels SET pinned_at = NULL WHERE name = ? AND pinned_at IS NOT NULL",
            (name,),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Channel '{name}' not found or not pinned")


def delete_channel(name: str) -> None:
    """Hard delete channel and all messages/bookmarks. Raises ValueError if not found."""
    with store.ensure("bridge") as conn:
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
        conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))


def list_channels(all: bool = False, agent_id: str | None = None) -> list[Channel]:
    """Get channels. With agent_id, returns active (unread) channels; otherwise all channels."""
    with store.ensure("bridge") as conn:
        if agent_id:
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
        else:
            archived_clause = "" if all else "AND c.archived_at IS NULL"
            query = f"""
                SELECT
                    c.channel_id,
                    c.name,
                    c.topic,
                    c.created_at,
                    c.archived_at,
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


def fetch_inbox(agent_id: str) -> list[Channel]:
    """Get all channels with unread messages for agent."""
    with store.ensure("bridge") as conn:
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


def get_channel(channel: str | Channel) -> Channel | None:
    """Get a channel by its ID, including members."""
    channel_id = _to_channel_id(channel)
    with store.ensure("bridge") as conn:
        row = conn.execute(
            "SELECT channel_id, name, topic, created_at, archived_at FROM channels WHERE channel_id = ?",
            (channel_id,),
        ).fetchone()

        if not row:
            return None

        channel = _row_to_channel(row)

        members_cursor = conn.execute(
            "SELECT DISTINCT agent_id FROM messages WHERE channel_id = ? ORDER BY agent_id",
            (channel_id,),
        )
        channel.members = [p_row["agent_id"] for p_row in members_cursor.fetchall()]
        return channel


def export_channel(channel: str | Channel) -> Export:
    """Get complete channel export with messages and notes."""
    channel_id = _to_channel_id(channel)
    channel = get_channel(channel_id)
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    messages = messaging.get_messages(channel_id)
    notes_list = notes.get_notes(channel_id)

    created_at = None
    if messages:
        created_at = messages[0].created_at

    return Export(
        channel_id=channel_id,
        channel_name=channel.name,
        topic=channel.topic,
        created_at=created_at,
        members=channel.members,
        message_count=len(messages),
        messages=messages,
        notes=notes_list,
    )

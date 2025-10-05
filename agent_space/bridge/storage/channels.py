"""Storage logic for channels."""

import sqlite3
import uuid

from ..models import Channel, ExportData
from .db import get_db_connection


def create_channel_record(channel_name: str, instruction_hash: str) -> str:
    """Create channel record in DB, locking instruction version. Returns channel_id."""
    channel_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO channels (id, name, instruction_hash) VALUES (?, ?, ?)",
            (channel_id, channel_name, instruction_hash),
        )
        conn.commit()
    return channel_id


def ensure_channel_exists(channel_name: str) -> str:
    """Ensure channel exists and return stable UUID."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT id FROM channels WHERE name = ?", (channel_name,))
        result = cursor.fetchone()

    if result:
        return result["id"]

    raise ValueError(
        f"Channel '{channel_name}' does not exist. Use coordination layer to create channels."
    )


def get_channel_id(channel_name: str) -> str:
    """Get stable channel ID from human-readable name."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT id FROM channels WHERE name = ?", (channel_name,))
        result = cursor.fetchone()

    if not result:
        raise ValueError(f"Channel '{channel_name}' not found")
    return result["id"]


def get_channel_name(channel_id: str) -> str | None:
    """Resolve a channel UUID back to its human-readable name."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT name FROM channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()
    return row["name"] if row else None


def set_context(channel_id: str, context: str):
    """Update channel context, but only if it's not already set."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE channels SET context = ? WHERE id = ? AND (context IS NULL OR context = '')",
            (context, channel_id),
        )
        conn.commit()


def get_context(channel_id: str) -> str | None:
    """Get channel context if it exists."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT context FROM channels WHERE id = ?", (channel_id,))
        result = cursor.fetchone()
    return result["context"] if result and result["context"] else None


def get_participants(channel_id: str) -> list[str]:
    """Get a sorted list of unique participants in a channel."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT DISTINCT sender FROM messages WHERE channel_id = ? ORDER BY sender",
            (channel_id,),
        )
        return [row["sender"] for row in cursor.fetchall()]


def fetch_channels(agent_id: str = None, time_filter: str = None) -> list[Channel]:
    """Get channels with metadata, optionally filtered by activity time and including unread counts for an agent."""
    with get_db_connection() as conn:
        query = """
            SELECT t.id, t.name, t.context, t.created_at,
                   COALESCE(msg_counts.total_messages, 0) as total_messages,
                   msg_counts.last_activity,
                   COALESCE(msg_counts.participants, '') as participants,
                   COALESCE(note_counts.notes_count, 0) as notes_count
            FROM channels t
            LEFT JOIN (
                SELECT channel_id,
                       COUNT(id) as total_messages,
                       MAX(created_at) as last_activity,
                       GROUP_CONCAT(DISTINCT sender) as participants
                FROM messages
                GROUP BY channel_id
            ) as msg_counts ON t.id = msg_counts.channel_id
            LEFT JOIN (
                SELECT channel_id,
                       COUNT(id) as notes_count
                FROM notes
                GROUP BY channel_id
            ) as note_counts ON t.id = note_counts.channel_id
        """
        params = []
        if time_filter:
            query += " WHERE t.created_at > datetime('now', ?) "
            params.append(time_filter)

        query += """
            ORDER BY t.created_at DESC
        """
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
                    context=row["context"],
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
    """Export a complete channel conversation for research purposes."""
    with get_db_connection() as conn:
        channel_cursor = conn.execute(
            "SELECT name, context, created_at FROM channels WHERE id = ?", (channel_id,)
        )
        channel_info = channel_cursor.fetchone()

        msg_cursor = conn.execute(
            "SELECT sender, content, created_at FROM messages WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        messages = [dict(row) for row in msg_cursor.fetchall()]

        note_cursor = conn.execute(
            "SELECT author, content, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        notes = [dict(row) for row in note_cursor.fetchall()]

    participants = sorted({msg["sender"] for msg in messages})

    return ExportData(
        channel_id=channel_id,
        channel_name=channel_info["name"] if channel_info else None,
        context=channel_info["context"] if channel_info else None,
        created_at=channel_info["created_at"] if channel_info else None,
        participants=participants,
        message_count=len(messages),
        messages=messages,
        notes=notes,
    )


def archive_channel(channel_id: str):
    """Archive a channel by setting its creation date to 30 days in the past."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE channels SET created_at = datetime('now', '-30 days') WHERE id = ?",
            (channel_id,),
        )
        conn.commit()


def delete_channel(channel_id: str):
    """Permanently delete a channel and all associated messages and bookmarks."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM bookmarks WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        conn.commit()


def rename_channel(old_name: str, new_name: str) -> bool:
    """Rename channel name only - UUID references remain stable. Returns True on success."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM channels WHERE name = ?", (old_name,))
            if not cursor.fetchone():
                return False
            cursor = conn.execute("SELECT 1 FROM channels WHERE name = ?", (new_name,))
            if cursor.fetchone():
                return False

            conn.execute("UPDATE channels SET name = ? WHERE name = ?", (new_name, old_name))
            conn.commit()
        return True
    except sqlite3.Error:
        return False


# Topic compatibility -------------------------------------------------------


def create_topic_record(topic_name: str, instruction_hash: str) -> str:
    """Backward compatible alias for channel creation."""
    return create_channel_record(topic_name, instruction_hash)


def ensure_topic_exists(topic_name: str) -> str:
    """Backward compatible alias for channel existence check."""
    return ensure_channel_exists(topic_name)


def get_topic_id(topic_name: str) -> str:
    """Backward compatible alias for channel lookup."""
    return get_channel_id(topic_name)


def archive_topic(topic_id: str) -> None:
    """Backward compatible alias for channel archival."""
    archive_channel(topic_id)


def delete_topic(topic_id: str) -> None:
    """Backward compatible alias for channel deletion."""
    delete_channel(topic_id)


def rename_topic(old_name: str, new_name: str) -> bool:
    """Backward compatible alias for channel renaming."""
    return rename_channel(old_name, new_name)

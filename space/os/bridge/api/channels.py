"""Channel operations: create, rename, archive, pin, list, resolve."""

import sqlite3
import uuid

from space.core.models import Channel
from space.lib import store
from space.lib.store import from_row


def _row_to_channel(row: store.Row) -> Channel:
    return from_row(row, Channel)


def _to_channel_id(channel: str | Channel) -> str:
    return channel.channel_id if isinstance(channel, Channel) else channel


def create_channel(name: str, topic: str | None = None) -> Channel:
    if not name:
        raise ValueError("Channel name is required")

    channel_id = uuid.uuid4().hex
    with store.ensure() as conn:
        conn.execute(
            "INSERT INTO channels (channel_id, name, topic) VALUES (?, ?, ?)",
            (channel_id, name, topic),
        )
    return Channel(channel_id=channel_id, name=name, topic=topic)


def rename_channel(old_name: str, new_name: str) -> bool:
    """Rename channel. Returns True if successful.

    Args:
        old_name: Current channel name (automatically stripped of # prefix).
        new_name: New channel name (automatically stripped of # prefix).

    Returns:
        True if successful, False if old_channel not found or new_channel exists.
    """
    old_name = old_name.lstrip("#")
    new_name = new_name.lstrip("#")
    with store.ensure() as conn:
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
    with store.ensure() as conn:
        cursor = conn.execute(
            "UPDATE channels SET archived_at = CURRENT_TIMESTAMP WHERE name = ? AND archived_at IS NULL",
            (name,),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Channel '{name}' not found or already archived")


def restore_channel(name: str) -> None:
    with store.ensure() as conn:
        cursor = conn.execute(
            "UPDATE channels SET archived_at = NULL WHERE name = ? AND archived_at IS NOT NULL",
            (name,),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Channel '{name}' not found or not archived")


def toggle_pin_channel(name: str) -> bool:
    """Toggle pin status of a channel. Returns True if pinned, False if unpinned. Raises ValueError if not found."""
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT pinned_at FROM channels WHERE name = ?",
            (name,),
        ).fetchone()
        if not row:
            raise ValueError(f"Channel '{name}' not found")

        is_pinned = row["pinned_at"] is not None
        if is_pinned:
            conn.execute(
                "UPDATE channels SET pinned_at = NULL WHERE name = ?",
                (name,),
            )
            return False
        conn.execute(
            "UPDATE channels SET pinned_at = CURRENT_TIMESTAMP WHERE name = ?",
            (name,),
        )
        return True


def delete_channel(name: str) -> None:
    """Hard delete channel and all messages. Raises ValueError if not found."""
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT channel_id FROM channels WHERE name = ?",
            (name,),
        ).fetchone()
        if not row:
            raise ValueError(f"Channel '{name}' not found")

        channel_id = row["channel_id"]
        conn.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))


def list_channels(all: bool = False) -> list[Channel]:
    """Get all channels."""
    with store.ensure() as conn:
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
                0 as unread_count
            FROM channels c
            LEFT JOIN messages m ON c.channel_id = m.channel_id
            WHERE 1=1 {archived_clause}
            GROUP BY c.channel_id
            ORDER BY COALESCE(MAX(m.created_at), c.created_at) DESC
        """
        cursor = conn.execute(query)
        return [_row_to_channel(row) for row in cursor.fetchall()]


def get_channel(channel: str | Channel) -> Channel | None:
    """Get a channel by its ID or name, including members."""
    channel_id = _to_channel_id(channel)
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT channel_id, name, topic, created_at, archived_at FROM channels WHERE channel_id = ? OR name = ?",
            (channel_id, channel_id),
        ).fetchone()

        if not row:
            return None

        channel = _row_to_channel(row)

        members_cursor = conn.execute(
            "SELECT DISTINCT agent_id FROM messages WHERE channel_id = ? ORDER BY agent_id",
            (channel.channel_id,),
        )
        channel.members = [p_row["agent_id"] for p_row in members_cursor.fetchall()]
        return channel


def count_channels() -> tuple[int, int, int]:
    """Get channel counts: (distinct_in_messages, active, archived).

    Distinct: channels with messages (used in stats)
    Active: channels not archived
    Archived: channels archived
    """
    with store.ensure() as conn:
        distinct = conn.execute("SELECT COUNT(DISTINCT channel_id) FROM messages").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM channels WHERE archived_at IS NULL").fetchone()[
            0
        ]
        archived = total - active
    return distinct, active, archived

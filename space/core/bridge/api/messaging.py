"""Message operations: send, receive, alerts, bookmarks."""

from space.core.models import Channel, Message
from space.lib import db
from space.lib.db import from_row
from space.lib.uuid7 import uuid7


def _row_to_message(row: db.Row) -> Message:
    return from_row(row, Message)


def _to_channel_id(channel: str | Channel) -> str:
    """Extract channel_id from Channel object or return string as-is."""
    return channel.channel_id if isinstance(channel, Channel) else channel


def send_message(channel: str | Channel, identity: str, content: str) -> str:
    """Send message. Returns agent_id."""
    from space.core import spawn

    channel_id = _to_channel_id(channel)
    if not identity:
        raise ValueError("identity is required")
    if not channel_id:
        raise ValueError("channel_id is required")

    agent_id = spawn.ensure_agent(identity)
    message_id = uuid7()
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            (message_id, channel_id, agent_id, content),
        )
    return agent_id


def get_messages(channel: str | Channel, agent_id: str | None = None) -> list[Message]:
    """Get messages, optionally filtering for new messages for a given agent."""
    channel_id = _to_channel_id(channel)
    with db.ensure("bridge") as conn:
        from . import channels

        channel = channels.get_channel(channel_id)
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")

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


def get_sender_history(identity: str, limit: int = 5) -> list[Message]:
    """Get recent messages from agent."""
    from space.core import spawn

    agent_id = spawn.ensure_agent(identity)
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


def set_bookmark(agent_id: str, channel: str | Channel, last_seen_id: str) -> None:
    """Mark message as read for agent."""
    channel_id = _to_channel_id(channel)
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks (agent_id, channel_id, last_seen_id) VALUES (?, ?, ?)",
            (agent_id, channel_id, last_seen_id),
        )


def recv_messages(
    channel: str | Channel, identity: str
) -> tuple[list[Message], int, str | None, list[str]]:
    """Receive new messages and update bookmark."""

    from space.core import spawn

    from . import channels

    channel_id = _to_channel_id(channel)

    agent_id = spawn.ensure_agent(identity)

    messages = get_messages(channel_id, agent_id)

    unread_count = len(messages)

    if messages:
        set_bookmark(agent_id, channel_id, messages[-1].message_id)

    channel = channels.get_channel(channel_id)

    topic = channel.topic if channel else None

    members = channel.members if channel else []

    return messages, unread_count, topic, members

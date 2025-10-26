"""Message operations: send, receive, alerts, bookmarks."""

import sqlite3

from space.core.models import Channel, Message
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7


def _row_to_message(row: store.Row) -> Message:
    return from_row(row, Message)


def _to_channel_id(channel: str | Channel) -> str:
    """Extract channel_id from Channel object or return string as-is."""
    return channel.channel_id if isinstance(channel, Channel) else channel


def send_message(channel: str | Channel, identity: str, content: str) -> str:
    """Send message. Returns agent_id."""
    from space.os import spawn

    channel_id = _to_channel_id(channel)
    if not identity:
        raise ValueError("identity is required")
    if not channel_id:
        raise ValueError("channel_id is required")
    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Identity '{identity}' not registered.")
    agent_id = agent.agent_id
    message_id = uuid7()
    with store.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            (message_id, channel_id, agent_id, content),
        )
    spawn.api.touch_agent(agent_id)
    return agent_id


def _build_pagination_query_and_params(
    conn: sqlite3.Connection, channel_id: str, last_seen_id: str | None, base_query: str
) -> tuple[str, tuple]:
    """Builds the SQL query and parameters for message pagination."""
    if last_seen_id is None:
        # If no last_seen_id, fetch all messages for the channel, ordered by creation time.
        query = f"{base_query} ORDER BY m.created_at"
        params = (channel_id,)
    else:
        # If last_seen_id is provided, find the message it refers to to get its created_at and rowid.
        last_seen_row = conn.execute(
            "SELECT created_at, rowid FROM messages WHERE message_id = ?", (last_seen_id,)
        ).fetchone()
        if last_seen_row:
            # Fetch messages created after the last seen message,
            # or messages created at the same time but with a greater rowid (for stable ordering).
            query = f"{base_query} AND (m.created_at > ? OR (m.created_at = ? AND m.rowid > ?)) ORDER BY m.created_at, m.rowid"
            params = (
                channel_id,
                last_seen_row["created_at"],
                last_seen_row["created_at"],
                last_seen_row["rowid"],
            )
        else:
            # If last_seen_id is invalid or not found, fall back to fetching all messages.
            query = f"{base_query} ORDER BY m.created_at"
            params = (channel_id,)
    return query, params


def get_messages(channel: str | Channel, agent_id: str | None = None) -> list[Message]:
    """Get messages, optionally filtering for new messages for a given agent."""
    channel_id = _to_channel_id(channel)
    with store.ensure("bridge") as conn:
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

        query, params = _build_pagination_query_and_params(
            conn, channel_id, last_seen_id, base_query
        )

        cursor = conn.execute(query, params)
        return [_row_to_message(row) for row in cursor.fetchall()]


def get_sender_history(identity: str, limit: int = 5) -> list[Message]:
    from space.os import spawn

    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Identity '{identity}' not registered.")
    agent_id = agent.agent_id
    with store.ensure("bridge") as conn:
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
    with store.ensure("bridge") as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks (agent_id, channel_id, last_seen_id) VALUES (?, ?, ?)",
            (agent_id, channel_id, last_seen_id),
        )


def recv_messages(
    channel: str | Channel, identity: str
) -> tuple[list[Message], int, str | None, list[str]]:
    """Receive new messages and update bookmark."""

    from space.os import spawn

    from . import channels

    channel_id = _to_channel_id(channel)

    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Identity '{identity}' not registered.")
    agent_id = agent.agent_id

    messages = get_messages(channel_id, agent_id)

    unread_count = len(messages)

    if messages:
        set_bookmark(agent_id, channel_id, messages[-1].message_id)

    channel = channels.get_channel(channel_id)

    topic = channel.topic if channel else None

    members = channel.members if channel else []

    return messages, unread_count, topic, members

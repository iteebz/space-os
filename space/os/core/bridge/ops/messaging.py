"""Message operations: send, receive, alerts, bookmarks."""

import sqlite3

from space.os import db
from space.os.db import from_row
from space.os.lib.uuid7 import uuid7
from space.os.models import BridgeMessage


def _row_to_message(row: sqlite3.Row) -> BridgeMessage:
    return from_row(row, BridgeMessage)


def send_message(channel_id: str, identity: str, content: str, priority: str = "normal") -> str:
    """Send message. Returns agent_id."""
    from .. import spawn

    if not identity:
        raise ValueError("identity is required")
    if not channel_id:
        raise ValueError("channel_id is required")

    agent_id = spawn.db.ensure_agent(identity)
    message_id = uuid7()
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content, priority) VALUES (?, ?, ?, ?, ?)",
            (message_id, channel_id, agent_id, content, priority),
        )
    return agent_id


def get_new_messages(channel_id: str, agent_id: str) -> list[BridgeMessage]:
    """Get messages newer than agent's last bookmark."""
    with db.ensure("bridge") as conn:
        from . import channels

        channels.get_channel_name(channel_id)

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
    """Get all messages in channel."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            "SELECT message_id, channel_id, agent_id, content, created_at FROM messages WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [_row_to_message(row) for row in cursor.fetchall()]


def get_alerts(agent_id: str) -> list[BridgeMessage]:
    """Get unread alert messages for agent."""
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
    """Get recent messages from agent."""
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


def set_bookmark(agent_id: str, channel_id: str, last_seen_id: str) -> None:
    """Mark message as read for agent."""
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks (agent_id, channel_id, last_seen_id) VALUES (?, ?, ?)",
            (agent_id, channel_id, last_seen_id),
        )


def recv_updates(channel_id: str, identity: str) -> tuple[list[BridgeMessage], int, str, list[str]]:
    """Receive new messages and update bookmark."""
    from .. import spawn
    from . import channels

    channel_name = channels.get_channel_name(channel_id)
    agent_id = spawn.db.ensure_agent(identity)

    messages = get_new_messages(channel_id, agent_id)

    if channel_name == "summary" and messages:
        messages = [messages[-1]]

    unread_count = len(messages)

    if messages:
        set_bookmark(agent_id, channel_id, messages[-1].message_id)

    topic = channels.get_topic(channel_id)
    participants = channels.get_participants(channel_id)
    return messages, unread_count, topic, participants

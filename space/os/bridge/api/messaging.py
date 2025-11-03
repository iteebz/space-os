"""Message operations: send, receive, format, history."""

import sqlite3
import time

from space.core.models import Channel, Message
from space.lib import store
from space.lib.codec import decode_base64
from space.lib.store import from_row
from space.lib.uuid7 import uuid7


def _row_to_message(row: store.Row) -> Message:
    return from_row(row, Message)


def _to_channel_id(channel: str | Channel) -> str:
    """Extract channel_id from Channel object or return string as-is."""
    return channel.channel_id if isinstance(channel, Channel) else channel


def send_message(
    channel: str | Channel, identity: str, content: str, decode_base64_flag: bool = False
) -> str:
    """Send message. Returns agent_id.

    Args:
        channel: Channel name or ID.
        identity: Sender identity (caller responsible for validation).
        content: Message content (or base64-encoded if decode_base64_flag=True).
        decode_base64_flag: If True, decode content from base64.

    Raises:
        ValueError: If channel not found, identity not registered, or base64 payload invalid.
    """
    from space.os import spawn

    from . import channels

    if decode_base64_flag:
        content = decode_base64(content)

    channel_id = _to_channel_id(channel)
    if not identity:
        raise ValueError("identity is required")
    if not channel_id:
        raise ValueError("channel_id is required")
    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Identity '{identity}' not registered.")
    agent_id = agent.agent_id

    channel_obj = channels.get_channel(channel_id)
    if not channel_obj:
        raise ValueError(f"Channel '{channel_id}' not found. Create it first with 'bridge create'.")
    actual_channel_id = channel_obj.channel_id

    message_id = uuid7()
    with store.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            (message_id, actual_channel_id, agent_id, content),
        )
    spawn.api.touch_agent(agent_id)

    from . import mentions

    mentions.spawn_from_mentions(actual_channel_id, content, agent_id)
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


def get_messages(channel: str | Channel) -> list[Message]:
    """Get all messages in a channel (used for context assembly during spawns)."""
    channel_id = _to_channel_id(channel)
    with store.ensure("bridge") as conn:
        from . import channels

        channel_obj = channels.get_channel(channel_id)
        if not channel_obj:
            raise ValueError(f"Channel {channel_id} not found")

        actual_channel_id = channel_obj.channel_id

        base_query = """
            SELECT m.message_id, m.channel_id, m.agent_id, m.content, m.created_at
            FROM messages m
            JOIN channels c ON m.channel_id = c.channel_id
            WHERE m.channel_id = ? AND c.archived_at IS NULL
            ORDER BY m.created_at
        """

        cursor = conn.execute(base_query, (actual_channel_id,))
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


def get_messages_before(channel: str | Channel, timestamp: str, limit: int = 1) -> list[Message]:
    """Get messages in channel created before a given timestamp, ordered by most recent first.

    Args:
        channel: Channel name or ID
        timestamp: ISO timestamp cutoff (messages before this time)
        limit: Maximum number of messages to return

    Returns:
        List of Message objects, ordered by creation time (newest first)
    """
    from . import channels

    channel_id = _to_channel_id(channel)
    with store.ensure("bridge") as conn:
        channel_obj = channels.get_channel(channel_id)
        if not channel_obj:
            raise ValueError(f"Channel {channel_id} not found")

        cursor = conn.execute(
            """
            SELECT m.message_id, m.channel_id, m.agent_id, m.content, m.created_at
            FROM messages m
            WHERE m.channel_id = ? AND m.created_at < ?
            ORDER BY m.created_at DESC
            LIMIT ?
            """,
            (channel_obj.channel_id, timestamp, limit),
        )
        return [_row_to_message(row) for row in cursor.fetchall()]


def recv_messages(
    channel: str | Channel, identity: str, ago: str | None = None
) -> tuple[list[Message], int, str | None, list[str]]:
    """Receive messages in channel, optionally filtered by time window.

    Args:
        channel: Channel name or ID.
        identity: Receiver identity (validated but not used for filtering).
        ago: Time window filter (e.g., '1h', '30m'). None = all messages.

    Returns:
        Tuple of (messages, count, topic, members)
    """
    from space.os import spawn

    from . import channels

    channel_id = _to_channel_id(channel)

    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Identity '{identity}' not registered.")

    messages = get_messages(channel_id)

    if ago:
        from datetime import datetime, timedelta

        match = __import__("re").match(r"(\d+)([hm])", ago)
        if not match:
            raise ValueError("Invalid time format. Use '1h' or '30m'")
        val, unit = int(match.group(1)), match.group(2)
        delta = timedelta(hours=val if unit == "h" else 0, minutes=val if unit == "m" else 0)
        cutoff = (datetime.now() - delta).isoformat()
        messages = [m for m in messages if m.created_at > cutoff]

    unread_count = len(messages)

    channel_obj = channels.get_channel(channel_id)

    topic = channel_obj.topic if channel_obj else None

    members = channel_obj.members if channel_obj else []

    return messages, unread_count, topic, members


def format_messages(messages: list[Message], title: str = "Messages", as_json: bool = False) -> str:
    """Format messages as markdown or JSON.

    Args:
        messages: List of Message objects.
        title: Header title (markdown only).
        as_json: If True, return JSON; otherwise return markdown.

    Returns:
        Formatted string (markdown or JSON).
    """
    import json

    from space.os import spawn

    if as_json:
        return json.dumps(
            [
                {
                    "message_id": msg.message_id,
                    "agent_id": msg.agent_id,
                    "content": msg.content,
                    "created_at": msg.created_at,
                }
                for msg in messages
            ],
            indent=2,
        )

    lines = [f"# {title}\n"]
    for msg in messages:
        sender = spawn.get_agent(msg.agent_id)
        sender_name = sender.identity if sender else msg.agent_id[:8]
        from datetime import datetime

        ts = datetime.fromisoformat(msg.created_at).strftime("%H:%M:%S")
        lines.append(f"**{sender_name}** ({ts}):")
        lines.append(msg.content)
        lines.append("")
    return "\n".join(lines)


def wait_for_message(
    channel: str | Channel, identity: str, session_id: str, poll_interval: float = 0.1
) -> tuple[list[Message], int, str | None, list[str]]:
    """Wait for a new message from others in a channel (blocking).

    Args:
        channel: Channel name or ID.
        identity: Receiver identity.
        session_id: Session ID for bookmark tracking.
        poll_interval: Polling interval in seconds.

    Returns:
        Tuple of (messages, count, context, participants) for messages from others.

    Raises:
        ValueError: If channel not found or identity not registered.
        KeyboardInterrupt: If user interrupts.
    """
    from space.os import spawn

    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Identity '{identity}' not registered.")
    agent_id = agent.agent_id
    channel_id = _to_channel_id(channel)

    while True:
        msgs, count, context, participants = recv_messages(channel_id, identity, session_id)
        other_messages = [msg for msg in msgs if msg.agent_id != agent_id]

        if other_messages:
            return other_messages, len(other_messages), context, participants

        time.sleep(poll_interval)


def count_messages() -> tuple[int, int, int]:
    """Get message counts: (total, active, archived).

    Total: all messages
    Active: messages in non-archived channels
    Archived: messages in archived channels
    """
    with store.ensure("bridge") as conn:
        total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        archived = conn.execute(
            "SELECT COUNT(*) FROM messages m WHERE m.channel_id IN "
            "(SELECT channel_id FROM channels WHERE archived_at IS NOT NULL)"
        ).fetchone()[0]
        active = total - archived
    return total, active, archived

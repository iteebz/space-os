"""Message operations: send, receive, format, history."""

import re
import time
from datetime import datetime, timedelta

from space.core.models import Channel, Message
from space.lib import store
from space.lib.codec import decode_base64 as decode_base64_content
from space.lib.store import from_row
from space.lib.uuid7 import uuid7

from .channels import _to_channel_id


def _row_to_message(row: store.Row) -> Message:
    return from_row(row, Message)


def send_message(
    channel: str | Channel, identity: str, content: str, decode_base64: bool = False
) -> str:
    from space.os import spawn

    from . import channels

    if decode_base64:
        content = decode_base64_content(content)

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
    with store.ensure() as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            (message_id, actual_channel_id, agent_id, content),
        )
    spawn.api.touch_agent(agent_id)

    from . import delimiters

    delimiters.spawn_from_mentions(actual_channel_id, content, agent_id)
    return agent_id


def get_messages(channel: str | Channel) -> list[Message]:
    channel_id = _to_channel_id(channel)
    with store.ensure() as conn:
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
    with store.ensure() as conn:
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
    from . import channels

    channel_id = _to_channel_id(channel)
    with store.ensure() as conn:
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
    channel: str | Channel, ago: str | None = None, reader_id: str | None = None
) -> tuple[list[Message], int, str | None, list[str]]:
    from . import channels

    channel_id = _to_channel_id(channel)
    channel_obj = channels.get_channel(channel_id)
    if not channel_obj:
        raise ValueError(f"Channel {channel_id} not found")

    actual_channel_id = channel_obj.channel_id
    messages = get_messages(channel_id)

    if ago:
        match = re.match(r"(\d+)([hm])", ago)
        if not match:
            raise ValueError("Invalid time format. Use '1h' or '30m'")
        val, unit = int(match.group(1)), match.group(2)
        delta = timedelta(hours=val if unit == "h" else 0, minutes=val if unit == "m" else 0)
        cutoff = (datetime.now() - delta).isoformat()
        messages = [m for m in messages if m.created_at > cutoff]
    elif reader_id:
        last_read_id = get_bookmark(reader_id, actual_channel_id)
        if last_read_id:
            found_bookmark = False
            filtered = []
            for m in messages:
                if found_bookmark:
                    filtered.append(m)
                elif m.message_id == last_read_id:
                    found_bookmark = True
            messages = filtered

    if reader_id and messages:
        update_bookmark(reader_id, actual_channel_id, messages[-1].message_id)

    unread_count = len(messages)
    topic = channel_obj.topic if channel_obj else None
    members = channel_obj.members if channel_obj else []

    return messages, unread_count, topic, members


def get_bookmark(reader_id: str, channel_id: str) -> str | None:
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT last_read_id FROM bookmarks WHERE reader_id = ? AND channel_id = ?",
            (reader_id, channel_id),
        ).fetchone()
        return row[0] if row else None


def update_bookmark(reader_id: str, channel_id: str, last_read_id: str) -> None:
    now = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            """
            INSERT INTO bookmarks (reader_id, channel_id, last_read_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (reader_id, channel_id) DO UPDATE SET
                last_read_id = excluded.last_read_id,
                updated_at = excluded.updated_at
            """,
            (reader_id, channel_id, last_read_id, now),
        )


def copy_bookmarks(from_reader_id: str, to_reader_id: str) -> None:
    now = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            """
            INSERT INTO bookmarks (reader_id, channel_id, last_read_id, updated_at)
            SELECT ?, channel_id, last_read_id, ?
            FROM bookmarks
            WHERE reader_id = ?
            ON CONFLICT (reader_id, channel_id) DO UPDATE SET
                last_read_id = excluded.last_read_id,
                updated_at = excluded.updated_at
            """,
            (to_reader_id, now, from_reader_id),
        )


def format_messages(messages: list[Message], title: str = "Messages", as_json: bool = False) -> str:
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
        ts = datetime.fromisoformat(msg.created_at).strftime("%H:%M:%S")
        lines.append(f"**{sender_name}** ({ts}):")
        lines.append(msg.content)
        lines.append("")
    return "\n".join(lines)


def wait_for_message(
    channel: str | Channel, identity: str, poll_interval: float = 0.1
) -> tuple[list[Message], int, str | None, list[str]]:
    from space.os import spawn

    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Identity '{identity}' not registered.")
    agent_id = agent.agent_id
    channel_id = _to_channel_id(channel)

    while True:
        msgs, count, context, participants = recv_messages(channel_id)
        other_messages = [msg for msg in msgs if msg.agent_id != agent_id]

        if other_messages:
            return other_messages, len(other_messages), context, participants

        time.sleep(poll_interval)


def count_messages() -> tuple[int, int, int]:
    with store.ensure() as conn:
        total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        archived = conn.execute(
            "SELECT COUNT(*) FROM messages m WHERE m.channel_id IN "
            "(SELECT channel_id FROM channels WHERE archived_at IS NOT NULL)"
        ).fetchone()[0]
        active = total - archived
    return total, active, archived

"""Storage logic for messages."""

from ..models import Message
from .db import get_db_connection


def create_message(
    channel_id: str, sender: str, content: str, prompt_hash: str, priority: str = "normal"
) -> int:
    """Insert a message record into the database."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO messages (channel_id, sender, content, prompt_hash, priority)
            VALUES (?, ?, ?, ?, ?)
        """,
            (channel_id, sender, content, prompt_hash, priority),
        )
        message_id = cursor.lastrowid
        conn.commit()
    return message_id


def get_new_messages(
    channel_id: str, agent_id: str, alerts_only: bool = False
) -> tuple[list[Message], int]:
    """Get unread messages for a specific agent in a channel."""
    with get_db_connection() as conn:
        # Get agent's last seen message ID
        cursor = conn.execute(
            "SELECT last_seen_id FROM bookmarks WHERE agent_id = ? AND channel_id = ?",
            (agent_id, channel_id),
        )
        result = cursor.fetchone()
        last_seen_id = result["last_seen_id"] if result else 0

        # Get messages since last seen
        if alerts_only:
            cursor = conn.execute(
                """
                SELECT id, channel_id, sender, content, created_at
                FROM messages
                WHERE channel_id = ? AND id > ? AND priority = 'alert'
                ORDER BY created_at ASC
            """,
                (channel_id, last_seen_id),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, channel_id, sender, content, created_at
                FROM messages
                WHERE channel_id = ? AND id > ?
                ORDER BY created_at ASC
            """,
                (channel_id, last_seen_id),
            )
        messages = [Message(**row) for row in cursor.fetchall()]

    return messages, len(messages)


def get_all_messages(channel_id: str) -> list[Message]:
    """Retrieve all messages for a given channel from storage."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, channel_id, sender, content, created_at
            FROM messages
            WHERE channel_id = ?
            ORDER BY created_at ASC
        """,
            (channel_id,),
        )
        return [Message(**row) for row in cursor.fetchall()]


def get_sender_history(sender: str, limit: int | None = None) -> list[Message]:
    """Retrieve all messages sent by sender across all channels."""
    with get_db_connection() as conn:
        if limit:
            cursor = conn.execute(
                """
                SELECT id, channel_id, sender, content, created_at
                FROM messages
                WHERE sender = ?
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (sender, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, channel_id, sender, content, created_at
                FROM messages
                WHERE sender = ?
                ORDER BY created_at DESC
            """,
                (sender,),
            )
        return [Message(**row) for row in cursor.fetchall()]

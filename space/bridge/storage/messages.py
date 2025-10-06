"""Storage logic for messages."""

from .. import models
from .db import get_db_connection

Message = models.Message


def create_message(
    channel_id: str,
    sender: str,
    content: str,
    prompt_hash: str,
    priority: str = "normal",
    constitution_hash: str | None = None,
) -> int:
    """Insert a message record into the database."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO messages (channel_id, sender, content, prompt_hash, priority, constitution_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (channel_id, sender, content, prompt_hash, priority, constitution_hash),
        )
        message_id = cursor.lastrowid
        conn.commit()
    return message_id


def get_new_messages(channel_id: str, last_seen_id: int | None = None) -> list[Message]:
    """Retrieve new messages since the last seen message ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if last_seen_id is None:
            cursor.execute(
                """
                SELECT m.id, m.channel_id, m.sender, m.content, m.created_at
                FROM messages m
                JOIN channels c ON m.channel_id = c.id
                WHERE m.channel_id = ? AND c.archived_at IS NULL
                ORDER BY m.id
                """,
                (channel_id,),
            )
        else:
            cursor.execute(
                """
                SELECT m.id, m.channel_id, m.sender, m.content, m.created_at
                FROM messages m
                JOIN channels c ON m.channel_id = c.id
                WHERE m.channel_id = ? AND m.id > ? AND c.archived_at IS NULL
                ORDER BY m.id
                """,
                (channel_id, last_seen_id),
            )
        messages = [Message(*row) for row in cursor.fetchall()]
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
    with get_db_connection() as conn:
        query = "SELECT id, channel_id, sender, content, created_at FROM messages WHERE sender = ? ORDER BY created_at DESC"
        params = (sender, limit) if limit else (sender,)
        if limit:
            query += " LIMIT ?"
        return [Message(**row) for row in conn.execute(query, params).fetchall()]

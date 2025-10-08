"""Storage logic for messages."""

from .. import models
from .db import get_db_connection

Message = models.Message


def create_message(channel_id: str, sender: str, content: str, priority: str = "normal") -> int:
    """Insert a message record into the database."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO messages (channel_id, sender, content, priority)
            VALUES (?, ?, ?, ?)
        """,
            (channel_id, sender, content, priority),
        )
        message_id = cursor.lastrowid
        conn.commit()
    return message_id


def _agent_last_seen_id(conn, channel_id: str, agent_id: str | None) -> int | None:
    """Resolve the last seen bookmark for an agent and channel."""
    if not agent_id:
        return None

    row = conn.execute(
        """
        SELECT last_seen_id
        FROM bookmarks
        WHERE agent_id = ? AND channel_id = ?
        """,
        (agent_id, channel_id),
    ).fetchone()
    return row["last_seen_id"] if row else None


def get_new_messages(channel_id: str, agent_id: str | None = None) -> list[Message]:
    """Retrieve new messages since the agent's bookmark (or all when unset)."""
    with get_db_connection() as conn:
        last_seen_id = _agent_last_seen_id(conn, channel_id, agent_id)
        params: tuple[str, ...] | tuple[str, int]

        base_query = """
            SELECT m.id, m.channel_id, m.sender, m.content, m.created_at
            FROM messages m
            JOIN channels c ON m.channel_id = c.id
            WHERE m.channel_id = ? AND c.archived_at IS NULL
        """

        if last_seen_id is None:
            query = f"{base_query} ORDER BY m.id"
            params = (channel_id,)
        else:
            query = f"{base_query} AND m.id > ? ORDER BY m.id"
            params = (channel_id, last_seen_id)

        cursor = conn.execute(query, params)
        return [Message(*row) for row in cursor.fetchall()]


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
    """Return most recent messages authored by the sender."""
    with get_db_connection() as conn:
        query = """
            SELECT id, channel_id, sender, content, created_at
            FROM messages
            WHERE sender = ?
            ORDER BY created_at DESC
        """
        params: tuple[str, ...] | tuple[str, int]
        if limit:
            query += " LIMIT ?"
            params = (sender, limit)
        else:
            params = (sender,)
        return [Message(**row) for row in conn.execute(query, params).fetchall()]

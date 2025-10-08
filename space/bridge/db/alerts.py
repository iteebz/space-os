"""Alert queries across all channels."""

from ..models import Message
from .db import get_db_connection


def get_alerts(agent_id: str) -> list[Message]:
    """Get all unread alerts across all channels for an agent."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT m.id, m.channel_id, m.sender, m.content, m.created_at
            FROM messages m
            LEFT JOIN bookmarks b ON m.channel_id = b.channel_id AND b.agent_id = ?
            WHERE m.priority = 'alert'
              AND (b.last_seen_id IS NULL OR m.id > b.last_seen_id)
            ORDER BY m.created_at DESC
        """,
            (agent_id,),
        )
        return [Message(**row) for row in cursor.fetchall()]

"""Storage logic for agent bookmarks (read state)."""

from .db import get_db_connection


def set_bookmark(agent_id: str, channel_id: str, last_seen_id: int):
    """Update agent's bookmark for a channel."""
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO bookmarks (agent_id, channel_id, last_seen_id)
            VALUES (?, ?, ?)
        """,
            (agent_id, channel_id, last_seen_id),
        )
        conn.commit()

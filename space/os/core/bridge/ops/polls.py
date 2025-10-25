"""Poll operations: create, dismiss, query."""

import uuid

from space.os import db


def create_poll(agent_id: str, channel_id: str, created_by: str = "human") -> str:
    """Create poll record. Returns poll_id."""
    poll_id = uuid.uuid4().hex
    with db.ensure("bridge") as conn:
        conn.execute(
            """
            INSERT INTO polls (poll_id, agent_id, channel_id, created_by)
            VALUES (?, ?, ?, ?)
            """,
            (poll_id, agent_id, channel_id, created_by),
        )
    return poll_id


def dismiss_poll(agent_id: str, channel_id: str) -> bool:
    """Dismiss active poll. Returns True if dismissed."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            """
            UPDATE polls SET poll_dismissed_at = CURRENT_TIMESTAMP
            WHERE agent_id = ? AND channel_id = ? AND poll_dismissed_at IS NULL
            """,
            (agent_id, channel_id),
        )
        return cursor.rowcount > 0


def get_active_polls(channel_id: str | None = None) -> list[dict]:
    """Get active polls (not dismissed)."""
    with db.ensure("bridge") as conn:
        if channel_id:
            cursor = conn.execute(
                """
                SELECT p.poll_id, p.agent_id, p.channel_id, p.poll_started_at
                FROM polls p
                WHERE p.channel_id = ? AND p.poll_dismissed_at IS NULL
                ORDER BY p.poll_started_at DESC
                """,
                (channel_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT p.poll_id, p.agent_id, p.channel_id, p.poll_started_at
                FROM polls p
                WHERE p.poll_dismissed_at IS NULL
                ORDER BY p.poll_started_at DESC
                """
            )
        return [dict(row) for row in cursor.fetchall()]


def is_polling(agent_id: str, channel_id: str) -> bool:
    """Check if agent has active poll in channel."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            """
            SELECT COUNT(*) as count FROM polls
            WHERE agent_id = ? AND channel_id = ? AND poll_dismissed_at IS NULL
            """,
            (agent_id, channel_id),
        )
        row = cursor.fetchone()
        return row["count"] > 0 if row else False

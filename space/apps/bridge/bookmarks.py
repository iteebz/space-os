"""Storage logic for agent bookmarks (read state)."""

from .db import connect


def set(
    agent_id: str, channel_id: str, last_seen_id: int, constitution_hash: str | None = None
):
    """Update agent's bookmark for a channel."""
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO bookmarks (agent_id, channel_id, last_seen_id, constitution_hash)
            VALUES (?, ?, ?, ?)
        """,
            (agent_id, channel_id, last_seen_id, constitution_hash),
        )
        conn.commit()

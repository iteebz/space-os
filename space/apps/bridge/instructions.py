"""Storage logic for managing and versioning coordination instructions."""

from .db import connect


def get_channel_instructions(channel_id: str) -> tuple[str, str, str] | None:
    """Get the locked instructions for a specific channel."""
    with connect() as conn:
        cursor = conn.execute(
            """
            SELECT ci.hash, ci.content, ci.notes
            FROM channels t
            JOIN instructions ci ON t.instruction_hash = ci.hash
            WHERE t.id = ?
            """,
            (channel_id,),
        )
        result = cursor.fetchone()
    return tuple(result) if result else None


def save_instructions(instruction_hash: str, content: str, notes: str = None):
    """Store instruction content if the hash is new."""
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO instructions (hash, content, notes) VALUES (?, ?, ?)",
            (instruction_hash, content, notes),
        )
        conn.commit()


def get_topic_instructions(channel_id: str) -> tuple[str, str, str] | None:
    """Backward compatible alias for legacy topic-based API."""
    return get_channel_instructions(channel_id)

"""Storage logic for channel notes."""

from .db import connect


def create(channel_id: str, author: str, content: str, prompt_hash: str) -> int:
    """Append a note to a channel, tracking author and prompt hash. Returns the new note ID."""
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO notes (channel_id, author, content, prompt_hash) VALUES (?, ?, ?, ?)",
            (channel_id, author, content, prompt_hash),
        )
        note_id = cursor.lastrowid
        conn.commit()
    return note_id


def fetch(channel_id: str) -> list[dict]:
    """Get all notes for a channel, identified by its ID."""
    with connect() as conn:
        cursor = conn.execute(
            "SELECT author, content, prompt_hash, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [
            {
                "author": row["author"],
                "content": row["content"],
                "prompt_hash": row["prompt_hash"][:8] if row["prompt_hash"] else "unknown",
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]

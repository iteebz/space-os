"""Storage logic for channel notes."""

from .db import get_db_connection


def create_note(channel_id: str, author: str, content: str) -> int:
    """Append a note to a channel, tracking author and prompt hash. Returns the new note ID."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO notes (channel_id, author, content) VALUES (?, ?, ?)",
            (channel_id, author, content),
        )
        note_id = cursor.lastrowid
        conn.commit()
    return note_id


def get_notes(channel_id: str) -> list[dict]:
    """Get all notes for a channel, identified by its ID."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT author, content, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [
            {
                "author": row["author"],
                "content": row["content"],
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]

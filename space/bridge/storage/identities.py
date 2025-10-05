"""Storage logic for agent identities and prompt file management."""

from .db import get_db_connection


def save_identity(base_identity: str, content: str, prompt_hash: str, notes: str = None):
    """Store identity content if hash is new and update active assignment."""
    with get_db_connection() as conn:
        # Store identity content if it's a new hash
        conn.execute(
            "INSERT OR IGNORE INTO identities (hash, base_identity, content, notes) VALUES (?, ?, ?, ?)",
            (prompt_hash, base_identity, content, notes),
        )
        conn.commit()


def base_identity(sender: str) -> str:
    """Extract base identity from a sender string (e.g., claude-1 -> claude, zealot-1 -> zealot)."""
    if sender == "detective":
        return "detective"
    if "-" in sender:
        return sender.split("-")[0]
    return sender


def get_senders(channel_id: str, base_identity: str) -> list[str]:
    """Get existing sender IDs in a channel that match a base identity pattern."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT DISTINCT sender FROM messages WHERE channel_id = ? AND sender LIKE ?",
            (channel_id, f"{base_identity}%"),
        )
        return [row["sender"] for row in cursor.fetchall()]


def active_hash(base_identity: str) -> str | None:
    """Retrieve the hash of the most recently saved identity for a given base identity."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT hash FROM identities WHERE base_identity = ? ORDER BY rowid DESC LIMIT 1",
            (base_identity,),
        )
        result = cursor.fetchone()
        return result["hash"] if result else None

from .db import connect
from .. import config
from space.apps.registry.guides import load_guide_content, hash_content, track_guide_in_registry


def get_channel(channel_id: str) -> tuple[str, str, str] | None:
    """Get the locked guide for a specific channel."""
    with connect() as conn:
        cursor = conn.execute(
            """
            SELECT g.hash, g.content, g.notes
            FROM channels c
            JOIN guides g ON c.guide_hash = g.hash
            WHERE c.id = ?
            """,
            (channel_id,),
        )
        result = cursor.fetchone()
    return tuple(result) if result else None


def save(guide_hash: str, content: str, notes: str = None):
    """Store guide content if the hash is new and track in registry."""
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO guides (hash, content, notes) VALUES (?, ?, ?)",
            (guide_hash, content, notes),
        )
        conn.commit()
    track_guide_in_registry(guide_hash, content)


def load_default() -> str:
    """Load the default bridge guide, hash it, and ensure it's tracked in the registry."""
    guide_content = load_guide_content("bridge")  # "bridge" is the guide_name
    guide_hash = hash_content(guide_content)
    save(guide_hash, guide_content, "default bridge guide")
    return guide_hash

# Backward compatible alias for legacy topic-based API.
# This will be removed once all callers are updated.
def get_topic_instructions(channel_id: str) -> tuple[str, str, str] | None:
    return get_channel(channel_id)

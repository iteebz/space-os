"""Business logic for handling channel notes."""

from .. import storage


def add_note(channel_id: str, identity: str, content: str):
    """Add a note to a channel, handling identity and channel resolution."""

    storage.create_note(channel_id, identity, content)


def get_notes(channel_id: str) -> list[dict]:
    """Get all notes for a channel."""
    return storage.get_notes(channel_id)

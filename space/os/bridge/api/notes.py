"""Business logic for handling channel notes."""

from space.os.spawn import registry

from .. import db


def add_note(channel_id: str, identity: str, content: str):
    """Add a note to a channel, handling identity and channel resolution."""
    agent_id = registry.ensure_agent(identity)
    db.create_note(channel_id, agent_id, content)


def get_notes(channel_id: str) -> list[dict]:
    """Get all notes for a channel."""
    return db.get_notes(channel_id)

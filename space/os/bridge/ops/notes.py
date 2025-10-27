"""Notes operations: get, add."""

from space.os.bridge.api import channels as ch
from space.os.bridge.api import notes as nt


def get_notes(channel: str):
    """Get all notes for a channel.

    Args:
        channel: Channel name or ID.

    Returns:
        List of note objects.

    Raises:
        ValueError: If channel not found.
    """
    channel_id = ch.resolve_channel(channel).channel_id
    return nt.get_notes(channel_id)


def add_note(channel: str, agent_id: str, content: str):
    """Add a note to a channel.

    Args:
        channel: Channel name or ID.
        agent_id: Agent ID adding the note (caller responsible for validation).
        content: Note content.

    Raises:
        ValueError: If channel not found.
    """
    channel_id = ch.resolve_channel(channel).channel_id
    return nt.add_note(channel_id, agent_id, content)

"""Channel operations: create, list, rename, archive, pin, unpin, delete."""

from space.os.bridge.api import channels as ch


def list_channels(all: bool = False):
    """List all channels.

    Returns:
        List of Channel objects (active, optionally archived).

    Raises:
        None
    """
    return ch.list_channels(all=all)


def create_channel(channel_name: str, topic: str | None = None):
    """Create a new channel.

    Args:
        channel_name: Name of the channel.
        topic: Optional channel topic.

    Returns:
        Channel ID.

    Raises:
        ValueError: If channel already exists or invalid name.
    """
    return ch.create_channel(channel_name, topic)


def rename_channel(old_channel: str, new_channel: str) -> bool:
    """Rename a channel.

    Args:
        old_channel: Current channel name (stripped of #).
        new_channel: New channel name (stripped of #).

    Returns:
        True if successful, False if old_channel not found or new_channel exists.

    Raises:
        None
    """
    old_channel = old_channel.lstrip("#")
    new_channel = new_channel.lstrip("#")
    return ch.rename_channel(old_channel, new_channel)


def archive_channel(channel_name: str):
    """Archive a single channel.

    Args:
        channel_name: Name of channel to archive.

    Raises:
        ValueError: If channel not found.
    """
    ch.archive_channel(channel_name)


def pin_channel(channel_name: str):
    """Pin a channel to favorites.

    Args:
        channel_name: Name of channel to pin.

    Raises:
        ValueError: If channel not found.
        TypeError: If invalid channel.
    """
    ch.pin_channel(channel_name)


def unpin_channel(channel_name: str):
    """Unpin a channel from favorites.

    Args:
        channel_name: Name of channel to unpin.

    Raises:
        ValueError: If channel not found.
        TypeError: If invalid channel.
    """
    ch.unpin_channel(channel_name)


def delete_channel(channel_name: str):
    """Delete a channel permanently.

    Args:
        channel_name: Name of channel to delete.

    Raises:
        ValueError: If channel not found.
    """
    ch.delete_channel(channel_name)


def fetch_inbox(agent_id: str):
    """Fetch inbox channels for an agent.

    Args:
        agent_id: Agent ID.

    Returns:
        List of Channel objects with unread messages.

    Raises:
        None
    """
    return ch.fetch_inbox(agent_id)

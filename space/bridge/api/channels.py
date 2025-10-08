from .. import storage
from ..models import Channel, ExportData


def active_channels(agent_id: str = None) -> list[Channel]:
    """Get active channels for dashboard display."""
    channels = storage.fetch_channels(agent_id, time_filter="-7 days")
    channels.sort(key=lambda t: t.last_activity if t.last_activity else "", reverse=True)
    return channels


def all_channels(agent_id: str = None) -> list[Channel]:
    """Get all channels."""
    return storage.fetch_channels(agent_id)


def export_channel(channel_name: str) -> ExportData:
    """Export complete channel conversation for research."""
    channel_id = storage.get_channel_id(channel_name)
    return storage.get_export_data(channel_id)


def archive_channel(channel_name: str):
    """Archive resolved channel."""
    channel_id = storage.get_channel_id(channel_name)
    storage.archive_channel(channel_id)


def delete_channel(channel_name: str):
    """Permanently delete channel and all messages."""
    channel_id = storage.get_channel_id(channel_name)
    storage.delete_channel(channel_id)


def rename_channel(old_name: str, new_name: str) -> bool:
    """Rename channel across all coordination data."""
    return storage.rename_channel(old_name, new_name)


def get_channel_context(channel_id: str) -> str | None:
    """Get the context for a specific channel."""
    return storage.get_context(channel_id)


def resolve_channel_id(channel_name: str) -> str:
    """Resolve channel name to UUID, creating channel if needed."""
    try:
        return storage.get_channel_id(channel_name)
    except ValueError:
        # Channel doesn't exist - create it
        return create_channel(channel_name)


def create_channel(channel_name: str) -> str:
    """Orchestrates the creation of a new channel."""
    return storage.create_channel_record(channel_name)

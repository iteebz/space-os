from .. import db
from ..models import Channel, ExportData


def active_channels(agent_id: str = None) -> list[Channel]:
    """Get active channels for dashboard display."""
    channels = db.fetch_channels(agent_id, time_filter="-7 days")
    channels.sort(key=lambda t: t.last_activity if t.last_activity else "", reverse=True)
    return channels


def all_channels(agent_id: str = None) -> list[Channel]:
    """Get all channels."""
    return db.fetch_channels(agent_id)


def export_channel(channel_name: str) -> ExportData:
    """Export complete channel conversation for research."""
    channel_id = db.get_channel_id(channel_name)
    return db.get_export_data(channel_id)


def archive_channel(channel_name: str):
    """Archive resolved channel."""
    channel_id = db.get_channel_id(channel_name)
    db.archive_channel(channel_id)


def delete_channel(channel_name: str):
    """Permanently delete channel and all messages."""
    channel_id = db.get_channel_id(channel_name)
    db.delete_channel(channel_id)


def rename_channel(old_name: str, new_name: str) -> bool:
    """Rename channel across all coordination data."""
    return db.rename_channel(old_name, new_name)


def get_channel_topic(channel_id: str) -> str | None:
    """Get the topic for a specific channel."""
    return db.get_topic(channel_id)


def resolve_channel_id(channel_name: str) -> str:
    """Resolve channel name to UUID, creating channel if needed."""
    from ...errors import ChannelNotFoundError
    
    try:
        return db.get_channel_id(channel_name)
    except ChannelNotFoundError:
        return create_channel(channel_name)


def create_channel(channel_name: str, topic: str | None = None) -> str:
    """Orchestrates the creation of a new channel."""
    return db.create_channel(channel_name, topic)

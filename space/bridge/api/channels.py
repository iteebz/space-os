from space.models import Channel, Export

from .. import db
from ..db import (
    fetch_channels,
    get_channel_id,
)


def active_channels(agent_id: str = None, limit: int = 5) -> list[Channel]:
    """Get active channels with unreads, limited to most recent."""
    channels = fetch_channels(agent_id, time_filter="-7 days", unread_only=True, active_only=True)
    channels.sort(key=lambda t: t.last_activity if t.last_activity else "", reverse=True)
    return channels[:limit]


def all_channels(agent_id: str = None) -> list[Channel]:
    """Get all channels."""
    return fetch_channels(agent_id, include_archived=True)


def inbox_channels(agent_id: str) -> list[Channel]:
    """Get all channels with unreads."""
    channels = fetch_channels(agent_id, unread_only=True, active_only=True)
    channels.sort(key=lambda t: t.last_activity if t.last_activity else "", reverse=True)
    return channels


def export_channel(channel_name: str) -> Export:
    channel_id = get_channel_id(channel_name)
    return db.get_export_data(channel_id)


def archive_channel(channel_name: str):
    """Archive resolved channel."""
    channel_id = get_channel_id(channel_name)
    db.archive_channel(channel_id)


def delete_channel(channel_name: str):
    """Permanently delete channel and all messages."""
    channel_id = get_channel_id(channel_name)
    db.delete_channel(channel_id)


def rename_channel(old_name: str, new_name: str) -> bool:
    """Rename channel across all coordination data."""
    return db.rename_channel(old_name, new_name)


def get_channel_topic(channel_id: str) -> str | None:
    """Get the topic for a specific channel."""
    return db.get_topic(channel_id)


def resolve_channel_id(channel_name: str) -> str:
    """Resolve channel name to UUID, creating channel if needed."""

    channel_id = get_channel_id(channel_name)
    if channel_id is None:
        channel_id = create_channel(channel_name)
    return channel_id


def create_channel(channel_name: str, topic: str | None = None) -> str:
    """Orchestrates the creation of a new channel."""
    return db.create_channel(channel_name, topic)

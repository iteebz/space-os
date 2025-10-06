import space.apps.bridge.channels as channels
import space.apps.bridge.utils as utils
import space.apps.bridge.instructions as instructions
from .models import Channel, ExportData


def active_channels(agent_id: str = None) -> list[Channel]:
    """Get active channels for dashboard display."""
    fetched_channels = channels.fetch_channels(agent_id, time_filter="-7 days")
    fetched_channels.sort(key=lambda t: t.last_activity if t.last_activity else "", reverse=True)
    return fetched_channels


def all_channels(agent_id: str = None) -> list[Channel]:
    """Get all channels."""
    return channels.fetch_channels(agent_id)


def export_channel(channel_name: str) -> ExportData:
    """Export complete channel conversation for research."""
    channel_id = channels.get_channel_id(channel_name)
    return channels.get_export_data(channel_id)


def archive_channel(channel_name: str):
    """Archive resolved channel."""
    channel_id = channels.get_channel_id(channel_name)
    channels.archive_channel(channel_id)


def delete_channel(channel_name: str):
    """Permanently delete channel and all messages."""
    channel_id = channels.get_channel_id(channel_name)
    channels.delete_channel(channel_id)


def rename_channel(old_name: str, new_name: str) -> bool:
    """Rename channel across all coordination data."""
    return channels.rename_channel(old_name, new_name)


def get_channel_context(channel_id: str) -> str | None:
    """Get the context for a specific channel."""
    return channels.get_context(channel_id)


def resolve_channel_id(channel_name: str) -> str:
    """Resolve channel name to UUID, creating channel if needed."""
    try:
        return channels.get_channel_id(channel_name)
    except ValueError:
        # Channel doesn't exist - create it
        return create_channel(channel_name)


def create_channel(channel_name: str) -> str:
    """Orchestrates the creation of a new channel with default instructions."""
    instructions.check_instructions()

    instructions_content = instructions.get_instructions()
    instruction_hash = utils.hash_content(instructions_content)

    instructions.save_instructions(instruction_hash, instructions_content, "default")

    return channels.create_channel_record(channel_name, instruction_hash)

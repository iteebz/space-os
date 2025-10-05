"""Backward compatible topic facade.

This layer preserves the legacy topic-oriented API so existing tooling keeps
working while the rest of the system migrates to channel terminology.
"""

from .. import storage, utils
from . import instructions


def active_channels(agent_id: str | None = None):
    channels = storage.fetch_channels(agent_id, time_filter="-7 days")
    channels.sort(key=lambda t: t.last_activity if t.last_activity else "", reverse=True)
    return channels


def all_channels(agent_id: str | None = None):
    return storage.fetch_channels(agent_id)


def export_channel(channel_name: str):
    channel_id = storage.get_channel_id(channel_name)
    return storage.get_export_data(channel_id)


def archive_channel(channel_name: str) -> None:
    channel_id = storage.get_channel_id(channel_name)
    storage.archive_channel(channel_id)


def delete_channel(channel_name: str) -> None:
    channel_id = storage.get_channel_id(channel_name)
    storage.delete_channel(channel_id)


def rename_channel(old_name: str, new_name: str) -> bool:
    return storage.rename_channel(old_name, new_name)


def get_channel_context(channel_id: str):
    return storage.get_context(channel_id)


def resolve_channel_id(channel_name: str) -> str:
    try:
        return storage.get_channel_id(channel_name)
    except ValueError:
        return create_channel(channel_name)


def create_channel(channel_name: str) -> str:
    instructions.check_instructions()
    instructions_content = instructions.get_instructions()
    instruction_hash = utils.hash_content(instructions_content)
    storage.save_instructions(instruction_hash, instructions_content, "default")
    return storage.create_channel_record(channel_name, instruction_hash)


__all__ = [
    "active_channels",
    "all_channels",
    "export_channel",
    "archive_channel",
    "delete_channel",
    "rename_channel",
    "get_channel_context",
    "resolve_channel_id",
    "create_channel",
]

"""Bridge operations: pure business logic, zero typer imports.

Functions handle all DB interactions and state management.
Callers: commands/ layer only.

Channel Lifecycle:
  create_channel(name) -> Channel with channel_id, created_at
  send_message(channel, content, agent_id) -> saves to messages table
  recv_messages(channel) -> list of Message objects from channel
  set_bookmark(agent, channel, message_id) -> track where agent last read
  fetch_inbox(agent_id) -> list of channels with unread_count
  toggle_pin_channel(name) -> sets/clears pinned_at timestamp
  archive_channel(name) -> soft delete via archived_at

Message Flow:
  send_message writes to messages table, touches last_activity
  recv_messages queries messages, returns newest first
  set_bookmark records last_seen_id per agent/channel pair
  Unread count derived from last_seen_id vs latest message
"""

from .channels import (
    archive_channel,
    create_channel,
    delete_channel,
    export_channel,
    fetch_inbox,
    get_channel,
    list_channels,
    rename_channel,
    resolve_channel,
    toggle_pin_channel,
)
from .mentions import spawn_from_mentions
from .messaging import (
    get_messages,
    get_sender_history,
    recv_messages,
    send_message,
    set_bookmark,
    wait_for_message,
)

__all__ = [
    "archive_channel",
    "create_channel",
    "delete_channel",
    "export_channel",
    "get_channel",
    "get_messages",
    "get_sender_history",
    "fetch_inbox",
    "list_channels",
    "recv_messages",
    "rename_channel",
    "resolve_channel",
    "send_message",
    "set_bookmark",
    "spawn_from_mentions",
    "toggle_pin_channel",
    "wait_for_message",
]

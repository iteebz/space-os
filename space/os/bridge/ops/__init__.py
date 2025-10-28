"""Bridge operations: pure business logic, zero framework knowledge.

Functions handle DB interactions and state management.
Fully testable, reusable anywhere (CLI, SDK, tests, automation).
Raise plain ValueError/TypeError on errors—no framework exceptions.
"""

from .channels import (
    archive_channel,
    create_channel,
    delete_channel,
    fetch_inbox,
    list_channels,
    pin_channel,
    rename_channel,
    unpin_channel,
)
from .messages import (
    recv_messages,
    send_message,
    wait_for_message,
)

__all__ = [
    "archive_channel",
    "create_channel",
    "delete_channel",
    "fetch_inbox",
    "list_channels",
    "pin_channel",
    "recv_messages",
    "rename_channel",
    "send_message",
    "unpin_channel",
    "wait_for_message",
]

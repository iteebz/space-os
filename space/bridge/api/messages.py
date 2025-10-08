"""Business logic for handling messages."""

import re

from .. import storage
from ..models import Message


def is_context(content: str) -> bool:
    """Check if a message content is intended to set the topic context."""
    context_patterns = [
        r"^CONTEXT:",
        r"^RESEARCH:",
        r"^REVIEW:",
        r"^DISCUSS:",
        r"^COORDINATE:",
        r"^PLAN:",
    ]
    return any(re.match(pattern, content, re.IGNORECASE) for pattern in context_patterns)


def parse_context(content: str) -> str:
    """Extract context from message, stripping prefix."""
    for prefix in ["CONTEXT:", "RESEARCH:", "REVIEW:", "DISCUSS:", "COORDINATE:", "PLAN:"]:
        if content.upper().startswith(prefix):
            return content[len(prefix) :].strip()
    return content


def send_message(channel_id: str, sender: str, content: str, priority: str = "normal") -> str:
    """Orchestrate sending a message: validate, ensure identity, and store."""
    storage.get_channel_name(channel_id)
    storage.create_message(
        channel_id=channel_id,
        sender=sender,
        content=content,
        priority=priority,
    )

    if is_context(content):
        context = parse_context(content)
        storage.set_context(channel_id, context)

    return sender


def recv_updates(channel_id: str, agent_id: str) -> tuple[list[Message], int, str, list[str]]:
    """Receive topic updates, returning messages, count, context, and participants."""
    messages = storage.get_new_messages(channel_id, agent_id)
    unread_count = len(messages)

    if messages:
        storage.set_bookmark(agent_id, channel_id, messages[-1].id)

    context = storage.get_context(channel_id)
    participants = storage.get_participants(channel_id)
    return messages, unread_count, context, participants


def fetch_messages(channel_id: str) -> list[Message]:
    """Retrieve all messages for a given topic."""
    return storage.get_all_messages(channel_id)


def fetch_sender_history(sender: str, limit: int | None = None) -> list[Message]:
    """Retrieve all messages from sender across all channels."""
    return storage.get_sender_history(sender, limit)

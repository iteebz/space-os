"""Business logic for handling messages."""

from .. import storage
from ..models import Message


def send_message(channel_id: str, sender: str, content: str, priority: str = "normal") -> str:
    """Orchestrate sending a message: validate, ensure identity, and store."""
    storage.get_channel_name(channel_id)
    storage.create_message(
        channel_id=channel_id,
        sender=sender,
        content=content,
        priority=priority,
    )

    return sender


def recv_updates(channel_id: str, agent_id: str) -> tuple[list[Message], int, str, list[str]]:
    """Receive topic updates, returning messages, count, context, and participants."""
    messages = storage.get_new_messages(channel_id, agent_id)
    unread_count = len(messages)

    if messages:
        storage.set_bookmark(agent_id, channel_id, messages[-1].id)

    topic = storage.get_topic(channel_id)
    participants = storage.get_participants(channel_id)
    return messages, unread_count, topic, participants


def fetch_messages(channel_id: str) -> list[Message]:
    """Retrieve all messages for a given topic."""
    return storage.get_all_messages(channel_id)


def fetch_sender_history(sender: str, limit: int | None = None) -> list[Message]:
    """Retrieve all messages from sender across all channels."""
    return storage.get_sender_history(sender, limit)

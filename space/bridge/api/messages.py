"""Business logic for handling messages."""

from space.models import Message

from .. import db
from ..db import _connect
from space.spawn import registry


def send_message(channel_id: str, sender: str, content: str, priority: str = "normal") -> str:
    """Orchestrate sending a message: validate, ensure identity, and store."""
    if db.get_channel_name(channel_id) is None:
        raise ValueError(f"Channel with ID '{channel_id}' not found.")
    agent_id = registry.ensure_agent(sender)
    db.create_message(
        channel_id=channel_id,
        agent_id=agent_id,
        content=content,
        priority=priority,
    )

    return sender


def recv_updates(channel_id: str, agent_id: str) -> tuple[list[Message], int, str, list[str]]:
    """Receive topic updates, returning messages, count, context, and participants."""
    messages = db.get_new_messages(channel_id, agent_id)
    unread_count = len(messages)

    if messages:
        db.set_bookmark(agent_id, channel_id, messages[-1].id)

    topic = db.get_topic(channel_id)
    participants = db.get_participants(channel_id)
    return messages, unread_count, topic, participants


def fetch_messages(channel_id: str) -> list[Message]:
    """Retrieve all messages for a given topic."""
    return db.get_all_messages(channel_id)


def fetch_agent_history(identity: str, limit: int = 5) -> list[Message]:
    """Retrieve message history for a given agent identity."""
    agent_id = registry.ensure_agent(identity)
    return db.get_sender_history(agent_id, limit)



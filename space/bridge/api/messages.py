"""Business logic for handling messages."""

from .. import db
from ..db import _connect
from ..models import Message


def send_message(channel_id: str, sender: str, content: str, priority: str = "normal") -> str:
    """Orchestrate sending a message: validate, ensure identity, and store."""
    db.get_channel_name(channel_id)
    db.create_message(
        channel_id=channel_id,
        sender=sender,
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


def fetch_agent_history(agent_name: str, limit: int | None = None) -> list[Message]:
    with _connect() as conn:
        query = "SELECT id, channel_id, sender, content, created_at FROM messages WHERE sender = ? ORDER BY created_at DESC"
        params = (agent_name, limit) if limit else (agent_name,)
        if limit:
            query += " LIMIT ?"
        return [Message(**row) for row in conn.execute(query, params).fetchall()]


def rename_agent(old_agent_name: str, new_agent_name: str):
    db.rename_agent_name(old_agent_name, new_agent_name)

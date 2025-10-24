"""Business logic for handling messages."""

import logging
import subprocess
import sys

from space.os.models import Message
from space.os.spawn import registry

from .. import db

log = logging.getLogger(__name__)


def send_message(channel_id: str, sender: str, content: str, priority: str = "normal") -> str:
    """Orchestrate sending a message: validate, ensure identity, and store."""
    agent_id = registry.ensure_agent(sender)
    db.create_message(
        channel_id=channel_id,
        agent_id=agent_id,
        content=content,
        priority=priority,
    )

    # Process @mentions only for non-system messages
    if sender != "system" and "@" in content:
        channel_name = db.get_channel_name(channel_id)
        log.debug(f"Spawning worker for channel={channel_name}, mentions in content")
        db.create_message(
            channel_id=channel_id,
            agent_id="system",
            content="[space] spawning agent(s)",
            priority="normal",
        )
        subprocess.Popen(
            [sys.executable, "-m", "space.bridge.worker", channel_id, channel_name, content],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    return agent_id


def recv_updates(channel_id: str, agent_id: str) -> tuple[list[Message], int, str, list[str]]:
    """Receive topic updates, returning messages, count, context, and participants."""
    channel_name = db.get_channel_name(channel_id)

    messages = db.get_new_messages(channel_id, agent_id)

    if channel_name == "summary" and messages:
        messages = [messages[-1]]

    unread_count = len(messages)

    if messages:
        db.set_bookmark(agent_id, channel_id, messages[-1].message_id)

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

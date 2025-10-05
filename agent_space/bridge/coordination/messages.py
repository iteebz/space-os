"""Business logic for handling messages."""

import re

from .. import storage
from ..models import Message
from .identities import load_identity
from .sentinel import log_security_event


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


def _store_identity(sender_id: str, topic: str):
    """Materialise identity content, enforcing provenance."""
    if sender_id in {"detective", "human"}:
        return sender_id
    identity_content, new_hash = load_identity(sender_id, topic)
    storage.save_identity(sender_id, identity_content, new_hash)
    return new_hash


def send_message(channel_id: str, sender: str, content: str) -> str:
    """Orchestrate sending a message: validate, ensure identity, and store."""
    topic = storage.get_channel_name(channel_id)
    prompt_hash = _store_identity(sender, topic)

    storage.create_message(
        channel_id=channel_id,
        sender=sender,
        content=content,
        prompt_hash=prompt_hash,
    )

    if is_context(content):
        context = parse_context(content)
        storage.set_context(channel_id, context)

    log_security_event(topic, sender, content)

    return sender


def recv_updates(channel_id: str, agent_id: str) -> tuple[list[Message], int, str, list[str]]:
    """Receive topic updates, returning messages, count, context, and participants."""
    messages, unread_count = storage.get_new_messages(channel_id, agent_id)

    if messages:
        storage.set_bookmark(agent_id, channel_id, messages[-1].id)

    context = storage.get_context(channel_id)
    participants = storage.get_participants(channel_id)
    return messages, unread_count, context, participants


def fetch_messages(channel_id: str) -> list[Message]:
    """Retrieve all messages for a given topic."""
    return storage.get_all_messages(channel_id)

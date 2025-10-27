"""Message operations: send, receive, wait."""

import base64
import binascii
import time

from space.os.bridge.api import channels as ch
from space.os.bridge.api import mentions, messaging


def send_message(channel: str, identity: str, content: str, decode_base64: bool = False):
    """Send a message to a channel.
    
    Args:
        channel: Channel name or ID.
        identity: Sender identity (caller responsible for validation).
        content: Message content (or base64-encoded if decode_base64=True).
        decode_base64: If True, decode content from base64.
    
    Raises:
        ValueError: If channel not found.
        ValueError: If base64 payload invalid.
    """
    if decode_base64:
        try:
            payload = base64.b64decode(content, validate=True)
            content = payload.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise ValueError("Invalid base64 payload") from exc

    channel_id = ch.resolve_channel(channel).channel_id
    messaging.send_message(channel_id, identity, content)
    mentions.spawn_from_mentions(channel_id, content)


def recv_messages(channel: str, agent_id: str):
    """Receive unread messages from a channel.
    
    Args:
        channel: Channel name or ID.
        agent_id: Agent ID (caller responsible for validation).
    
    Returns:
        Tuple of (messages, count, context, participants).
    
    Raises:
        ValueError: If channel not found.
    """
    channel_id = ch.resolve_channel(channel).channel_id
    return messaging.recv_messages(channel_id, agent_id)


def wait_for_message(channel: str, agent_id: str, poll_interval: float = 0.1):
    """Wait for a new message from others in a channel (blocking).
    
    Args:
        channel: Channel name or ID.
        agent_id: Agent ID (caller responsible for validation).
        poll_interval: Polling interval in seconds.
    
    Returns:
        Tuple of (messages, count, context, participants) for messages from others.
    
    Raises:
        ValueError: If channel not found.
        KeyboardInterrupt: If user interrupts.
    """
    channel_id = ch.resolve_channel(channel).channel_id

    while True:
        msgs, count, context, participants = messaging.recv_messages(channel_id, agent_id)
        other_messages = [msg for msg in msgs if msg.agent_id != agent_id]

        if other_messages:
            return other_messages, len(other_messages), context, participants

        time.sleep(poll_interval)

"""Business logic for alerts."""

from .. import storage
from ..models import Message


def get_alerts(agent_id: str) -> list[Message]:
    """Get all unread alerts across all channels for an agent."""
    return storage.get_alerts(agent_id)

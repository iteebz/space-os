"""Business logic for alerts."""

from space.os.models import BridgeMessage

from .. import db


def get_alerts(agent_id: str) -> list[BridgeMessage]:
    """Get all unread alerts across all channels for an agent."""
    return db.get_alerts(agent_id)

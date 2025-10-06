"""Business logic for alerts."""

import space.apps.bridge.alerts as alerts
from .models import Message


def get_alerts(agent_id: str) -> list[Message]:
    """Get all unread alerts across all channels for an agent."""
    return alerts.get_alerts(agent_id)

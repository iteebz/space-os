"""Summary-specific operations."""

from space.os.models import Memory


def get_summary(agent_id: str, limit: int = 1) -> list[Memory]:
    """Get summary entries for agent."""
    from space.os import spawn

    from . import get_memories

    role = spawn.db.get_agent_name(agent_id)
    return get_memories(role, topic="summary", limit=limit)


def add_summary(agent_id: str, message: str) -> str:
    """Add a summary entry."""
    from . import add_entry

    return add_entry(agent_id, "summary", message)


def update_summary(agent_id: str, message: str, note: str = "") -> str:
    """Update summary: replace existing with new version."""
    from . import replace_entry

    existing = get_summary(agent_id, limit=1)
    if not existing:
        return add_summary(agent_id, message)

    old_entry = existing[0]
    return replace_entry(
        [old_entry.memory_id], agent_id, "summary", message, note or "Updated summary"
    )

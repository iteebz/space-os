"""Context primitive: unified retrieval across 5 domains (memory, knowledge, bridge, chats, canon)."""

from space.os.context.api import collect_current_state, collect_timeline

__all__ = ["collect_timeline", "collect_current_state"]

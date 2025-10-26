"""DEPRECATED: Use space.core.chats instead.

This module has been migrated to space.core.chats as a first-class primitive.

Migration path:
    OLD: from space.lib import chats
    NEW: from space.core import chats
    
New features:
    - sessions/syncs table for offset-based sync
    - Provider abstraction (Claude, Codex, Gemini)
    - discover() for session discovery
    - link() for identity/task correlation
"""

from space.core import chats

sync = chats.sync
search = chats.search
discover = chats.discover
get_by_identity = chats.get_by_identity
get_by_task_id = chats.get_by_task_id
link = chats.link
export = chats.export

__all__ = [
    "sync",
    "search",
    "discover",
    "get_by_identity",
    "get_by_task_id",
    "link",
    "export",
]

# space/bridge/api.py

# Imports from other bridge modules
from .alerts import fetch as fetch_alerts
from .channels import archive, delete, export, rename as rename_channel, get_id, resolve_id as resolve_channel_id
from .messages import fetch_history as fetch_sender_history, fetch_all as get_all_messages, fetch_new as get_new_messages, create as create_message, send as send_message
from .notes import create as add_note, fetch as get_notes

# Imports from registry.guides (new source of truth for instructions)
from space.apps.registry.guides import load_guide_content, hash_content, track_guide_in_registry

# Other bridge imports
from .db import connect as get_bridge_db_connection
from .db import init as init_bridge_db
from .events import emit as emit_bridge_event
from .renderer import Event, Renderer
from .utils import format_local_time, format_time_ago, hash_content as utils_hash_content, hash_digest

# --- New functions for bridge instructions ---
def get_bridge_instructions() -> str:
    """Retrieve the default bridge instructions from the registry or file system."""
    return load_guide_content("bridge")

def save_bridge_instructions(content: str):
    """Save and track bridge instructions in the registry."""
    guide_hash = hash_content(content)
    track_guide_in_registry(guide_hash, content)
# --- End new functions ---


__all__ = [
    "fetch_alerts",
    "archive",
    "delete",
    "export",
    "rename_channel",
    "resolve_channel_id",

    "create_message",
    "fetch_sender_history",
    "get_all_messages",
    "get_new_messages",
    "send_message",
    "add_note",
    
    "get_bridge_instructions", # New
    "save_bridge_instructions", # New

    "init_bridge_db",
    "get_bridge_db_connection",
    # Events
    "emit_bridge_event",
    # Renderer
    "Event",
    "Renderer",

    # Utils (note: hash_content is now from registry.guides, so aliasing utils.hash_content)
    "utils_hash_content", # Aliased to avoid conflict
    "hash_digest",
    "format_local_time",
    "format_time_ago",
]
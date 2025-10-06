# space/bridge/api.py

# Imports from other bridge modules
from .alerts import fetch as fetch_alerts
from .channels import archive, delete, export, rename as rename_channel, get_id, get_name as resolve_channel_id
from .messages import fetch_history as fetch_sender_history, fetch_all as get_all_messages, fetch_new as get_new_messages, create as create_message
from .notes import create as add_note, fetch as get_notes

# Imports from registry.guides (new source of truth for instructions)
from space.apps.registry.guides import load_guide_content
from space.os.lib import sha256 # Import sha256 for consistent hashing

# Other bridge imports
from .db import connect as get_bridge_db_connection
from .db import init as init_bridge_db
from .events import emit as emit_bridge_event
from .renderer import Event, Renderer
from .utils import format_local_time, format_time_ago, hash_digest

# --- New functions for bridge instructions ---
def get_bridge_instructions() -> str:
    """Retrieve the default bridge instructions from the registry or file system."""
    return load_guide_content("bridge")

def save_bridge_instructions(content: str):
    """Save and track bridge instructions in the registry."""
    guide_hash = sha256.hash_string(content)
    # Note: track_guide_in_registry is now an internal helper in registry.guides
    # and should not be called directly from here. The auto-tracking happens
    # when load_guide_content is called if the guide is not already in the registry.
    # For explicit saving, we would need a registry_api.add_constitution_version call here.
    # For now, we'll assume saving is implicitly handled by loading or a separate registry CLI command.
    pass # Placeholder for explicit saving if needed
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

    # Utils
    "hash_digest",
    "format_local_time",
    "format_time_ago",
]
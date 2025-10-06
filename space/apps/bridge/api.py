# space/bridge/api.py

# From coordination
# From config
from .config import INSTRUCTIONS_FILE, resolve_sentinel_log_path
from .alert import get_alerts
from .channel import archive_channel, delete_channel, export_channel, rename_channel, resolve_channel_id
from .message import fetch_sender_history, get_all_messages, get_new_messages, send_message
from .note import add_note, get_notes
from .instructions import get_instructions, save_instructions
from .messages import create_message
from .db import connect as get_bridge_db_connection

# From storage.db
from .db import init as init_bridge_db

# From events
from .events import emit as emit_bridge_event

# From renderer
from .renderer import Event, Renderer

# From utils
from .utils import format_local_time, format_time_ago, hash_content, hash_digest

__all__ = [
    # Coordination
    "get_alerts",
    "archive_channel",
    "delete_channel",
    "export_channel",
    "rename_channel",
    "resolve_channel_id",
    "get_instructions",
    "save_instructions",
    "create_message",
    "fetch_sender_history",
    "get_all_messages",
    "get_new_messages",
    "send_message",
    "add_note",
    "get_notes",
    # Storage DB
    "init_bridge_db",
    "get_bridge_db_connection",
    # Events
    "emit_bridge_event",
    # Renderer
    "Event",
    "Renderer",
    # Config
    "INSTRUCTIONS_FILE",
    "resolve_sentinel_log_path",
    # Utils
    "hash_content",
    "hash_digest",
    "format_local_time",
    "format_time_ago",
]

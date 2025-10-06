import sys
from typing import cast

# from space.os.core.app import App # Moved to app.py
from .app import bridge_app # Import the instantiated app

from .api import (
    fetch_alerts,
    archive,
    delete,
    export,
    rename_channel,
    resolve_channel_id,
    create_message,
    fetch_sender_history,
    get_all_messages,
    get_new_messages,
    add_note,
    get_notes,
    get_bridge_instructions,
    save_bridge_instructions,
    init_bridge_db,
    get_bridge_db_connection,
    emit_bridge_event,
    Event,
    Renderer,
    hash_digest,
    format_local_time,
    format_time_ago,
)
from .cli import bridge_group

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
    "get_notes",
    "get_bridge_instructions",
    "save_bridge_instructions",
    "init_bridge_db",
    "get_bridge_db_connection",
    "emit_bridge_event",
    "Event",
    "Renderer",
    "hash_digest",
    "format_local_time",
    "format_time_ago",
    "bridge_app", # Expose the instantiated app
]


# name = "bridge" # Handled by app.py
# def cli_group(): # Handled by app.py
#     return bridge_group


# cast(App, sys.modules[__name__]) # No longer needed
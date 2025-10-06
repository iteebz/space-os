# This file defines the public API for the space.memory module.

from . import app
from .memory import clear, delete, edit, memorize, recall

def add_memory_entry(identity: str, topic: str, message: str) -> None:
    memorize(app.db_path, identity, topic, message)

def get_memory_entries(identity: str, topic: str | None = None) -> list:
    return recall(app.db_path, identity, topic)

def edit_memory_entry(entry_uuid: str, new_message: str) -> None:
    edit(app.db_path, entry_uuid, new_message)

def delete_memory_entry(entry_uuid: str) -> None:
    delete(app.db_path, entry_uuid)

def clear_memory_entries(identity: str, topic: str | None = None) -> None:
    clear(app.db_path, identity, topic)

__all__ = [
    "add_memory_entry",
    "get_memory_entries",
    "edit_memory_entry",
    "delete_memory_entry",
    "clear_memory_entries",
]
# This file defines the public API for the space.memory module.

from .models import Memory # Import Memory for type hinting
from space.os.events import emit # Import emit
from pathlib import Path # Import Path for type hinting

_memory_app_instance = None

def _set_memory_app_instance(app_instance: object):
    global _memory_app_instance
    _memory_app_instance = app_instance

def add_memory_entry(identity: str, topic: str, message: str) -> None:
    if _memory_app_instance is None:
        raise RuntimeError("Memory app instance not initialized in API.")
    memory_repository = _memory_app_instance.repositories['memory']
    entry_uuid = memory_repository.add(identity, topic, message)
    emit("memory", "entry.add", identity, {"topic": topic, "message": message[:50], "uuid": str(entry_uuid)})

def get_memory_entries(identity: str, topic: str | None = None) -> list[Memory]:
    if _memory_app_instance is None:
        raise RuntimeError("Memory app instance not initialized in API.")
    memory_repository = _memory_app_instance.repositories['memory']
    return memory_repository.get(identity, topic)

def edit_memory_entry(entry_uuid: str, new_message: str) -> None:
    if _memory_app_instance is None:
        raise RuntimeError("Memory app instance not initialized in API.")
    memory_repository = _memory_app_instance.repositories['memory']
    memory_repository.update(entry_uuid, new_message)
    emit("memory", "entry.edit", None, {"uuid": entry_uuid[-8:]})

def delete_memory_entry(entry_uuid: str) -> None:
    if _memory_app_instance is None:
        raise RuntimeError("Memory app instance not initialized in API.")
    memory_repository = _memory_app_instance.repositories['memory']
    memory_repository.delete(entry_uuid)
    emit("memory", "entry.delete", None, {"uuid": entry_uuid[-8:]})

def clear_memory_entries(identity: str, topic: str | None = None) -> None:
    if _memory_app_instance is None:
        raise RuntimeError("Memory app instance not initialized in API.")
    memory_repository = _memory_app_instance.repositories['memory']
    memory_repository.clear(identity, topic)
    # No specific emit for clear, as it can affect multiple entries.

__all__ = [
    "add_memory_entry",
    "get_memory_entries",
    "edit_memory_entry",
    "delete_memory_entry",
    "clear_memory_entries",
]
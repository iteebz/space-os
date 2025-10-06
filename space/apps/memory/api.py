# This file defines the public API for the space.memory module.

from .models import Memory # Import Memory for type hinting
from space.os.events import track # Import track
from pathlib import Path # Import Path for type hinting

_memory_repo_instance = None

def _set_memory_repo_instance(repo_instance: object):
    global _memory_repo_instance
    _memory_repo_instance = repo_instance

def add_memory_entry(identity: str, topic: str, message: str) -> None:
    if _memory_repo_instance is None:
        raise RuntimeError("Memory repository instance not initialized in API.")
    memory_repository = _memory_repo_instance
    entry_uuid = memory_repository.add(identity, topic, message)
    track(source="memory", event_type="entry.add", identity=identity, data={"topic": topic, "message": message[:50], "uuid": str(entry_uuid)})

def get_memory_entries(identity: str, topic: str | None = None) -> list[Memory]:
    if _memory_repo_instance is None:
        raise RuntimeError("Memory repository instance not initialized in API.")
    memory_repository = _memory_repo_instance
    return memory_repository.get(identity, topic)

def edit_memory_entry(entry_uuid: str, new_message: str) -> None:
    if _memory_repo_instance is None:
        raise RuntimeError("Memory repository instance not initialized in API.")
    memory_repository = _memory_repo_instance
    memory_repository.update(entry_uuid, new_message)
    track(source="memory", event_type="entry.edit", identity=None, data={"uuid": entry_uuid[-8:]})

def delete_memory_entry(entry_uuid: str) -> None:
    if _memory_repo_instance is None:
        raise RuntimeError("Memory repository instance not initialized in API.")
    memory_repository = _memory_repo_instance
    memory_repository.delete(entry_uuid)
    track(source="memory", event_type="entry.delete", identity=None, data={"uuid": entry_uuid[-8:]})

def clear_memory_entries(identity: str, topic: str | None = None) -> None:
    if _memory_repo_instance is None:
        raise RuntimeError("Memory repository instance not initialized in API.")
    memory_repository = _memory_repo_instance
    memory_repository.clear(identity, topic)
    # No specific track for clear, as it can affect multiple entries.

__all__ = [
    "add_memory_entry",
    "get_memory_entries",
    "edit_memory_entry",
    "delete_memory_entry",
    "clear_memory_entries",
    "_set_memory_repo_instance", # Expose the setter function
]
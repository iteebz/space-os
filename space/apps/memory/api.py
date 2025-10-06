from .models import Memory
from space.os.events import track
from pathlib import Path
from .repo import MemoryRepo # Import MemoryRepo for type hinting

def add_memory_entry(repo: MemoryRepo, identity: str, topic: str, message: str) -> None:
    entry_uuid = repo.add(identity, topic, message)
    track(source="memory", event_type="entry.add", identity=identity, data={"topic": topic, "message": message[:50], "uuid": str(entry_uuid)})

def get_memory_entries(repo: MemoryRepo, identity: str, topic: str | None = None) -> list[Memory]:
    return repo.get(identity, topic)

def edit_memory_entry(repo: MemoryRepo, entry_uuid: str, new_message: str) -> None:
    repo.update(entry_uuid, new_message)
    track(source="memory", event_type="entry.edit", identity=None, data={"uuid": entry_uuid[-8:]})

def delete_memory_entry(repo: MemoryRepo, entry_uuid: str) -> None:
    repo.delete(entry_uuid)
    track(source="memory", event_type="entry.delete", identity=None, data={"uuid": entry_uuid[-8:]})

def clear_memory_entries(repo: MemoryRepo, identity: str, topic: str | None = None) -> None:
    repo.clear(identity, topic)

__all__ = [
    "add_memory_entry",
    "get_memory_entries",
    "edit_memory_entry",
    "delete_memory_entry",
    "clear_memory_entries",
]
from pathlib import Path

from space.os.core.events import emit
from .repository import MemoryRepository
from .models import Memory # Still need Memory for type hinting in recall

def memorize(db_path: Path, identity: str, topic: str, message: str) -> str:
    repo = MemoryRepository(db_path)
    entry_uuid = repo.add(identity, topic, message)
    emit("memory", "entry.add", identity, {"topic": topic, "message": message[:50]})
    return entry_uuid

def recall(db_path: Path, identity: str, topic: str | None = None) -> list[Memory]:
    repo = MemoryRepository(db_path)
    return repo.get(identity, topic)

def edit(db_path: Path, entry_uuid: str, new_message: str):
    repo = MemoryRepository(db_path)
    repo.update(entry_uuid, new_message)
    # The emit for edit needs the full_uuid, which is internal to repo.update.
    # For now, we'll emit with the provided entry_uuid.
    emit("memory", "entry.edit", None, {"uuid": entry_uuid[-8:]})

def delete(db_path: Path, entry_uuid: str):
    repo = MemoryRepository(db_path)
    repo.delete(entry_uuid)
    # The emit for delete needs the full_uuid, which is internal to repo.delete.
    # For now, we'll emit with the provided entry_uuid.
    emit("memory", "entry.delete", None, {"uuid": entry_uuid[-8:]})

def clear(db_path: Path, identity: str, topic: str | None = None):
    repo = MemoryRepository(db_path)
    repo.clear(identity, topic)
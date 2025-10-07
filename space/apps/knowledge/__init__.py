"""The knowledge app, a repository for learned patterns."""
from dataclasses import dataclass

from space.os import events
from . import repository


@dataclass
class Knowledge:
    id: str
    domain: str
    contributor: str
    content: str
    confidence: float | None
    created_at: str


def write_knowledge(
    domain: str,
    contributor: str,
    content: str,
    confidence: float | None = None,
) -> str:
    """Write a knowledge entry."""
    repository.initialize() # Ensure schema exists
    entry_id = repository.add(domain, contributor, content, confidence)
    events.track(
        source="knowledge",
        event_type="write",
        identity=contributor,
        data={"id": entry_id, "domain": domain},
    )
    return entry_id


def query_knowledge(
    domain: str | None = None,
    contributor: str | None = None,
    entry_id: str | None = None,
) -> list[Knowledge]:
    """Query knowledge entries."""
    repository.initialize() # Ensure schema exists
    return repository.get(domain, contributor, entry_id)


def edit_knowledge(entry_id: str, new_content: str, new_confidence: float | None = None) -> None:
    """Edit a knowledge entry."""
    repository.initialize() # Ensure schema exists
    repository.update(entry_id, new_content, new_confidence)
    events.track(source="knowledge", event_type="edit", data={"id": entry_id})


def delete_knowledge(self, entry_id: str) -> None:
    """Delete a knowledge entry."""
    repository.initialize() # Ensure schema exists
    repository.delete(entry_id)
    events.track(source="knowledge", event_type="delete", data={"id": entry_id})


__all__ = [
    "write_knowledge",
    "query_knowledge",
    "edit_knowledge",
    "delete_knowledge",
    "Knowledge",
]

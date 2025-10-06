# This file defines the public API for the space.knowledge module.

from space.os import events
from space.os.lib import uuid7

from .models import Knowledge # Import Knowledge from models.py
from .repo import KnowledgeRepo # Import KnowledgeRepo for type hinting

class KnowledgeApi:
    def __init__(self, repo: KnowledgeRepo):
        self.repo = repo

    def write_knowledge(
        self,
        domain: str,
        contributor: str,
        content: str,
        confidence: float | None = None,
    ) -> str:
        entry_id = self.repo.add(domain, contributor, content, confidence)

        events.track(
            source="knowledge",
            event_type="write",
            identity=contributor,
            data={"id": entry_id, "domain": domain},
        )
        return entry_id

    def query_knowledge(
        self,
        domain: str | None = None,
        contributor: str | None = None,
        entry_id: str | None = None,
    ) -> list[Knowledge]:
        return self.repo.get(domain, contributor, entry_id)

    def edit_knowledge(self, entry_id: str, new_content: str, new_confidence: float | None = None) -> None:
        self.repo.update(entry_id, new_content, new_confidence)
        events.track(source="knowledge", event_type="edit", data={"id": entry_id})

    def delete_knowledge(self, entry_id: str) -> None:
        self.repo.delete(entry_id)
        events.track(source="knowledge", event_type="delete", data={"id": entry_id})

__all__ = [
    "KnowledgeApi",
]
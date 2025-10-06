from typing import Optional

from space.os import events
from .repo import SpawnRepo
from .models import Identity

repo = SpawnRepo()

def add_identity(id: str, type: str, initial_constitution_content: Optional[str] = None) -> Identity:
    identity = repo.add_identity(id, type)
    if initial_constitution_content:
        events.track(
            source="spawn",
            event_type="identity.created",
            identity=id,
            data={
                "identity_id": id,
                "identity_type": type,
                "initial_constitution_content": initial_constitution_content,
            },
        )
    return identity

def get_identity(id: str) -> Optional[Identity]:
    return repo.get_identity(id)

__all__ = [
    "add_identity",
    "get_identity",
]

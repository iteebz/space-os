from datetime import datetime

from . import repository
from .models import Memory

def add_memory(identity: str, topic: str, message: str):
    """Adds a memory to the store."""
    repository.initialize()
    repository.add(identity, topic, message)

def get_all_memories() -> list[Memory]:
    """Retrieves all memories from the store."""
    repository.initialize()
    return repository.get_all()

__all__ = ["add_memory", "get_all_memories", "Memory"]

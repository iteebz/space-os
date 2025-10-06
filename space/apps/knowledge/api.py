# This file defines the public API for the space.knowledge module.

from . import app
from .knowledge import query, write

def write_knowledge(domain: str, contributor: str, content: str, confidence: float | None = None) -> str:
    return write(app.db_path, domain, contributor, content, confidence)

def query_knowledge(domain: str | None = None, contributor: str | None = None, entry_id: str | None = None) -> list:
    return query(app.db_path, domain, contributor, entry_id)

__all__ = [
    "write_knowledge",
    "query_knowledge",
]

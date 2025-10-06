import sqlite3

from space.os import events
from space.os.lib import uuid7

from .app import knowledge_app as app
from .models import Knowledge # Import Knowledge from models.py


def write(
    domain: str,
    contributor: str,
    content: str,
    confidence: float | None = None,
) -> str:
    repo = app.repositories["knowledge"]
    entry_id = repo.add(domain, contributor, content, confidence)

    events.track(
        source="knowledge",
        event_type="write",
        identity=contributor,
        data={"id": entry_id, "domain": domain},
    )
    return entry_id


def query(
    domain: str | None = None,
    contributor: str | None = None,
    entry_id: str | None = None,
) -> list[Knowledge]:
    repo = app.repositories["knowledge"]
    return repo.get(domain, contributor, entry_id)

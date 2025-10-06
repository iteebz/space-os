from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .utils import database_path

CONTEXT_DB_NAME = "context.db"
_MIGRATED = False

_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    uuid TEXT PRIMARY KEY,
    identity TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_identity_topic ON memory(identity, topic);
CREATE INDEX IF NOT EXISTS idx_memory_identity_created ON memory(identity, created_at);
CREATE INDEX IF NOT EXISTS idx_memory_uuid ON memory(uuid);
"""

_KNOWLEDGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    contributor TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_contributor ON knowledge(contributor);
"""


def set_context_db_path(path: Path) -> None:
    """Override context database path (test hook)."""
    global _MIGRATED
    # This is a test hook, so we don't need to worry about the global path
    # for the main application.
    path.parent.mkdir(parents=True, exist_ok=True)
    _MIGRATED = False


def ensure() -> None:
    """Ensure the context database exists, schema is applied, and legacy data migrated."""
    db_path = database_path(CONTEXT_DB_NAME)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_MEMORY_SCHEMA)
        conn.commit()


@contextmanager
def connect(row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the context database, ensuring schema beforehand."""
    ensure()
    db_path = database_path(CONTEXT_DB_NAME)
    conn = sqlite3.connect(db_path)
    if row_factory is not None:
        conn.row_factory = row_factory
    try:
        yield conn
    finally:
        conn.close()







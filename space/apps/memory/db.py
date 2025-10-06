from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from space.os.lib.db_utils import database_path

MEMORY_DB_NAME = "memory.db"
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


def set_memory_db_path(path: Path) -> None:
    """Override memory database path (test hook)."""
    global _MIGRATED
    path.parent.mkdir(parents=True, exist_ok=True)
    _MIGRATED = False


def ensure() -> None:
    """Ensure the memory database exists and schema is applied."""
    db_path = database_path(MEMORY_DB_NAME)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_MEMORY_SCHEMA)
        conn.commit()


@contextmanager
def connect(row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the memory database, ensuring schema beforehand."""
    ensure()
    db_path = database_path(MEMORY_DB_NAME)
    conn = sqlite3.connect(db_path)
    if row_factory is not None:
        conn.row_factory = row_factory
    try:
        yield conn
    finally:
        conn.close()

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# database_path is no longer directly used here

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


def ensure_schema(db_path: Path) -> None:
    """Ensure the knowledge database schema is applied."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_KNOWLEDGE_SCHEMA)
        conn.commit()


@contextmanager
def connect(db_path: Path, row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the knowledge database."""
    conn = sqlite3.connect(db_path)
    if row_factory is not None:
        conn.row_factory = row_factory
    try:
        yield conn
    finally:
        conn.close()

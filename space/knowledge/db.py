from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from ..lib import db_utils  # Import the general db utility
from ..lib.ids import uuid7  # Assuming uuid7 is in lib.ids

KNOWLEDGE_DB_NAME = "knowledge.db"

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


@dataclass
class Entry:
    id: str
    domain: str
    contributor: str
    content: str
    confidence: float | None
    created_at: str


def database_path() -> Path:
    """Return absolute path to the knowledge database file."""
    return db_utils.database_path(KNOWLEDGE_DB_NAME)


def ensure_database(initializer: Callable[[sqlite3.Connection], None] | None = None) -> Path:
    """Ensure the knowledge database exists and schema is applied."""
    path = database_path()
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_KNOWLEDGE_SCHEMA)
        if initializer is not None:
            initializer(conn)
        conn.commit()
    return path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Yield a connection to the knowledge database, ensuring schema beforehand."""
    ensure_database()
    conn = sqlite3.connect(database_path())
    try:
        yield conn
    finally:
        conn.close()


def write_knowledge(
    domain: str, contributor: str, content: str, confidence: float | None = None
) -> str:
    entry_id = uuid7()
    with connect() as conn:
        conn.execute(
            "INSERT INTO knowledge (id, domain, contributor, content, confidence) VALUES (?, ?, ?, ?, ?)",
            (entry_id, domain, contributor, content, confidence),
        )
        conn.commit()
    return entry_id


def query_by_domain(domain: str) -> list[Entry]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge WHERE domain = ? ORDER BY created_at DESC",
            (domain,),
        ).fetchall()
    return [Entry(*row) for row in rows]


def query_by_contributor(contributor: str) -> list[Entry]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge WHERE contributor = ? ORDER BY created_at DESC",
            (contributor,),
        ).fetchall()
    return [Entry(*row) for row in rows]


def list_all() -> list[Entry]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge ORDER BY created_at DESC"
        ).fetchall()
    return [Entry(*row) for row in rows]


def get_by_id(entry_id: str) -> Entry | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge WHERE id = ?",
            (entry_id,),
        ).fetchone()
    return Entry(*row) if row else None

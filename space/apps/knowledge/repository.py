from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Iterator

from space.os.lib import uuid7
from . import Knowledge

# The path to the database, resolved relative to the OS data directory
# This follows the "OS as Library" principle
from space.os.paths import data_for
DB_PATH = data_for("knowledge") / "knowledge.db"

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

def initialize():
    """Ensure the database schema is applied."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_KNOWLEDGE_SCHEMA)
        conn.commit()

@contextmanager
def _connect(row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the knowledge database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row if row_factory is None else row_factory
    try:
        yield conn
    finally:
        conn.close()

def _row_to_entity(row: sqlite3.Row) -> Knowledge:
    return Knowledge(
        id=row["id"],
        domain=row["domain"],
        contributor=row["contributor"],
        content=row["content"],
        confidence=row["confidence"],
        created_at=row["created_at"],
    )

def add(domain: str, contributor: str, content: str, confidence: float | None = None) -> str:
    entry_id = str(uuid7.uuid7())
    created_at_timestamp = datetime.now().isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO knowledge (id, domain, contributor, content, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (entry_id, domain, contributor, content, confidence, created_at_timestamp),
        )
        conn.commit()
    return entry_id

def get(domain: str | None = None, contributor: str | None = None, entry_id: str | None = None) -> list[Knowledge]:
    query = "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge WHERE 1=1"
    params = []

    if entry_id:
        query += " AND id LIKE ?"
        params.append(f"{entry_id}%")
    if domain:
        query += " AND domain = ?"
        params.append(domain)
    if contributor:
        query += " AND contributor = ?"
        params.append(contributor)

    query += " ORDER BY created_at DESC"

    with _connect() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_row_to_entity(row) for row in rows]

def update(entry_id: str, new_content: str, new_confidence: float | None = None):
    query = "UPDATE knowledge SET content = ?"
    params = [new_content]
    if new_confidence is not None:
        query += ", confidence = ?"
        params.append(new_confidence)
    query += " WHERE id = ?"
    params.append(entry_id)
    with _connect() as conn:
        conn.execute(query, tuple(params))
        conn.commit()

def delete(entry_id: str):
    with _connect() as conn:
        conn.execute("DELETE FROM knowledge WHERE id = ?", (entry_id,))
        conn.commit()
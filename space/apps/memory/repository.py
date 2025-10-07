from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Iterator

from space.os.lib import uuid7
from .models import Memory

from space.os.paths import data_for
DB_PATH = data_for("memory")

_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    uuid TEXT PRIMARY KEY,
    identity TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
"""

def initialize():
    """Ensure the database schema is applied."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_MEMORY_SCHEMA)
        conn.commit()

@contextmanager
def _connect(row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the memory database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row if row_factory is None else row_factory
    try:
        yield conn
    finally:
        conn.close()

def _row_to_entity(row: sqlite3.Row) -> Memory:
    return Memory(
        uuid=row["uuid"],
        identity=row["identity"],
        topic=row["topic"],
        message=row["message"],
        created_at=row["created_at"],
    )

def add(identity: str, topic: str, message: str):
    with _connect() as conn:
        created_at = int(datetime.now().timestamp())
        conn.execute(
            "INSERT INTO memories (uuid, identity, topic, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (uuid7.uuid7(), identity, topic, message, created_at),
        )
        conn.commit()

def get_all() -> list[Memory]:
    with _connect() as conn:
        rows = conn.execute("SELECT uuid, identity, topic, message, created_at FROM memories ORDER BY created_at DESC").fetchall()
    return [_row_to_entity(row) for row in rows]
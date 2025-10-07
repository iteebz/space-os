from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Iterator
import json

from space.os.lib import uuid7
from .models import Event

from space.os.paths import data_for
DB_PATH = data_for("events") / "events.db"

_EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    identity TEXT,
    data TEXT,
    timestamp INTEGER NOT NULL
);
"""

def initialize():
    """Ensure the database schema is applied."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_EVENTS_SCHEMA)
        conn.commit()

@contextmanager
def _connect(row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the events database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row if row_factory is None else row_factory
    try:
        yield conn
    finally:
        conn.close()

def _row_to_entity(row: sqlite3.Row) -> Event:
    return Event(
        id=row["id"],
        timestamp=row["timestamp"],
        source=row["source"],
        event_type=row["event_type"],
        identity=row["identity"],
        data=json.loads(row["data"]) if row["data"] else None,
    )

def add(source: str, event_type: str, identity: str | None, data: dict | None) -> str:
    event_id = str(uuid7.uuid7())
    timestamp = int(datetime.now().timestamp())
    data_json = json.dumps(data) if data else None

    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (id, source, event_type, identity, data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, source, event_type, identity, data_json, timestamp),
        )
        conn.commit()
    return event_id

def get_all() -> list[Event]:
    with _connect() as conn:
        rows = conn.execute("SELECT id, source, event_type, identity, data, timestamp FROM events ORDER BY timestamp DESC").fetchall()
    return [_row_to_entity(row) for row in rows]
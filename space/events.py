import time
from pathlib import Path

from .lib import db as libdb
from .lib.ids import uuid7

DB_PATH = Path.cwd() / ".space" / "events.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    identity TEXT,
    event_type TEXT NOT NULL,
    data TEXT,
    timestamp INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_identity ON events(identity);
CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_id ON events(id);
"""


def _ensure_db():
    if not DB_PATH.exists():
        libdb.ensure_schema(DB_PATH, SCHEMA)


def _connect():
    return libdb.connect(DB_PATH)


def emit(source: str, event_type: str, identity: str | None = None, data: str | None = None):
    """Emit event to append-only log."""
    _ensure_db()
    event_id = uuid7()
    event_timestamp = int(time.time())

    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (id, source, identity, event_type, data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, source, identity, event_type, data, event_timestamp),
        )
        conn.commit()


def query(source: str | None = None, identity: str | None = None, limit: int = 100):
    """Query events by source or identity."""
    if not DB_PATH.exists():
        return []

    with _connect() as conn:
        if source and identity:
            rows = conn.execute(
                "SELECT id, source, identity, event_type, data, timestamp FROM events WHERE source = ? AND identity = ? ORDER BY id DESC LIMIT ?",
                (source, identity, limit),
            ).fetchall()
        elif source:
            rows = conn.execute(
                "SELECT id, source, identity, event_type, data, timestamp FROM events WHERE source = ? ORDER BY id DESC LIMIT ?",
                (source, limit),
            ).fetchall()
        elif identity:
            rows = conn.execute(
                "SELECT id, source, identity, event_type, data, timestamp FROM events WHERE identity = ? ORDER BY id DESC LIMIT ?",
                (identity, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, source, identity, event_type, data, timestamp FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

    return rows

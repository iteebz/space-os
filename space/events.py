import sqlite3
import time
from pathlib import Path

from .lib.ids import uuid7

DB_PATH = Path.cwd() / ".space" / "events.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    uuid TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    identity TEXT,
    event_type TEXT NOT NULL,
    data TEXT,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_identity ON events(identity);
CREATE INDEX IF NOT EXISTS idx_created_at ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_uuid ON events(uuid);
"""


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def emit(source: str, event_type: str, identity: str | None = None, data: str | None = None):
    """Emit event to append-only log."""
    init_db()
    event_uuid = uuid7()
    created_at = int(time.time())

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO events (uuid, source, identity, event_type, data, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (event_uuid, source, identity, event_type, data, created_at),
    )
    conn.commit()
    conn.close()


def query(source: str | None = None, identity: str | None = None, limit: int = 100):
    """Query events by source or identity."""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)

    if source and identity:
        rows = conn.execute(
            "SELECT uuid, source, identity, event_type, data, created_at FROM events WHERE source = ? AND identity = ? ORDER BY uuid DESC LIMIT ?",
            (source, identity, limit),
        ).fetchall()
    elif source:
        rows = conn.execute(
            "SELECT uuid, source, identity, event_type, data, created_at FROM events WHERE source = ? ORDER BY uuid DESC LIMIT ?",
            (source, limit),
        ).fetchall()
    elif identity:
        rows = conn.execute(
            "SELECT uuid, source, identity, event_type, data, created_at FROM events WHERE identity = ? ORDER BY uuid DESC LIMIT ?",
            (identity, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT uuid, source, identity, event_type, data, created_at FROM events ORDER BY uuid DESC LIMIT ?",
            (limit,),
        ).fetchall()

    conn.close()
    return rows

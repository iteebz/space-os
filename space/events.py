import time
from pathlib import Path

from .lib import db, paths
from .lib.ids import uuid7

DB_PATH = paths.space_root() / "events.db"

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

def _migrate_schema(db_path: Path):
    with db.connect(db_path) as conn:
        cursor = conn.execute("PRAGMA table_info(events)")
        columns = {row[1] for row in cursor.fetchall()}

        if "agent_id" not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN agent_id TEXT")
            conn.commit()

def _connect():
    if not DB_PATH.exists():
        db.ensure_schema(DB_PATH, SCHEMA)
    _migrate_schema(DB_PATH)
    return db.connect(DB_PATH)


def emit(source: str, event_type: str, agent_id: str | None = None, data: str | None = None):
    """Emit event to append-only log."""
    event_id = uuid7()
    event_timestamp = int(time.time())

    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (id, source, event_type, data, timestamp, agent_id) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, source, event_type, data, event_timestamp, agent_id),
        )
        conn.commit()


def query(source: str | None = None, agent_id: str | None = None, limit: int = 100):
    """Query events by source or agent_id."""
    if not DB_PATH.exists():
        return []

    with _connect() as conn:
        if source and agent_id:
            rows = conn.execute(
                "SELECT id, source, agent_id, event_type, data, timestamp FROM events WHERE source = ? AND agent_id = ? ORDER BY id DESC LIMIT ?",
                (source, agent_id, limit),
            ).fetchall()
        elif source:
            rows = conn.execute(
                "SELECT id, source, agent_id, event_type, data, timestamp FROM events WHERE source = ? ORDER BY id DESC LIMIT ?",
                (source, limit),
            ).fetchall()
        elif agent_id:
            rows = conn.execute(
                "SELECT id, source, agent_id, event_type, data, timestamp FROM events WHERE agent_id = ? ORDER BY id DESC LIMIT ?",
                (agent_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, source, agent_id, event_type, data, timestamp FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

    return rows


def identify(identity: str, command: str):
    """Provenance: track identity invocation.

    Creates immutable audit trail linking identity → command.
    """
    from .lib.identity import constitute_identity
    from .spawn import registry

    constitute_identity(identity)
    agent_id = registry.ensure_agent(identity)
    emit("identity", command, agent_id, "")

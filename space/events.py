import sqlite3
import time
from collections import namedtuple

from space import db

from .lib import paths
from .lib.identity import constitute_identity
from .lib.uuid7 import uuid7
from .spawn import registry

Event = namedtuple("Event", ["id", "source", "agent_id", "event_type", "data", "timestamp"])

DB_PATH = paths.dot_space() / "events.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    agent_id TEXT,
    event_type TEXT NOT NULL,
    data TEXT,
    timestamp INTEGER NOT NULL,
    session_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_agent_id ON events(agent_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_id ON events(id);
"""


def _add_column_if_not_exists(
    conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str
):
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cursor.fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        conn.commit()


def connect():
    return db.ensure("events")


def _migrate_add_agent_id(conn: sqlite3.Connection):
    _add_column_if_not_exists(conn, "events", "agent_id", "TEXT")


def _migrate_add_session_id(conn: sqlite3.Connection):
    _add_column_if_not_exists(conn, "events", "session_id", "TEXT")


db.register("events", "events.db", SCHEMA)

db.add_migrations(
    "events",
    [
        ("add_agent_id_to_events", _migrate_add_agent_id),
        ("add_session_id_to_events", _migrate_add_session_id),
    ],
)


def emit(
    source: str,
    event_type: str,
    agent_id: str | None = None,
    data: str | None = None,
):
    """Emit event to append-only log."""
    event_id = uuid7()
    event_timestamp = int(time.time())

    with connect() as conn:
        conn.execute(
            "INSERT INTO events (id, source, event_type, data, timestamp, agent_id) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, source, event_type, data, event_timestamp, agent_id),
        )


def query(source: str | None = None, agent_id: str | None = None, limit: int = 100):
    """Query events by source or agent_id."""
    if not DB_PATH.exists():
        return []

    with connect() as conn:
        query_parts = []
        params = []

        if source:
            query_parts.append("source = ?")
            params.append(source)
        if agent_id:
            query_parts.append("agent_id = ?")
            params.append(agent_id)

        where_clause = "WHERE " + " AND ".join(query_parts) if query_parts else ""
        params.append(limit)

        rows = conn.execute(
            f"SELECT id, source, agent_id, event_type, data, timestamp FROM events {where_clause} ORDER BY id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
        return [Event(*row) for row in rows]


def identify(identity: str, command: str):
    """Provenance: track identity invocation.

    Creates immutable audit trail linking identity → command.
    """
    constitute_identity(identity)
    agent_id = registry.ensure_agent(identity)
    emit("identity", command, agent_id, "")


def get_session_count(agent_id: str) -> int:
    """Count completed sessions (session_start events)."""
    with connect() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM events WHERE agent_id = ? AND event_type = 'session_start'",
            (agent_id,),
        ).fetchone()
        return result[0] if result else 0


def get_sleep_count(agent_id: str) -> int:
    """Count sleep events for an agent."""
    with connect() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM events WHERE agent_id = ? AND event_type = 'sleep'",
            (agent_id,),
        ).fetchone()
        return result[0] if result else 0


def get_wake_count(agent_id: str) -> int:
    """Count wake events for an agent."""
    with connect() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM events WHERE agent_id = ? AND event_type = 'wake'",
            (agent_id,),
        ).fetchone()
        return result[0] if result else 0


def get_last_sleep_time(agent_id: str) -> int | None:
    """Get timestamp of last sleep event for an agent."""
    with connect() as conn:
        result = conn.execute(
            "SELECT timestamp FROM events WHERE agent_id = ? AND event_type = 'sleep' ORDER BY timestamp DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        return result[0] if result else None


def get_wakes_since_last_sleep(agent_id: str) -> int:
    """Count wake events since last sleep (in current spawn)."""
    with connect() as conn:
        result = conn.execute(
            """SELECT COUNT(*) FROM events
               WHERE agent_id = ? AND event_type = 'wake'
               AND timestamp > COALESCE(
                   (SELECT MAX(timestamp) FROM events
                    WHERE agent_id = ? AND event_type = 'sleep'), 0)""",
            (agent_id, agent_id),
        ).fetchone()
        return result[0] if result else 0

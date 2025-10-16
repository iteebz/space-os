import sqlite3
import time
from collections import namedtuple
from contextlib import contextmanager

from .lib import db, paths
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


def _migrate_add_agent_id(conn: sqlite3.Connection):
    _add_column_if_not_exists(conn, "events", "agent_id", "TEXT")


def _migrate_add_session_id(conn: sqlite3.Connection):
    _add_column_if_not_exists(conn, "events", "session_id", "TEXT")


events_migrations = [
    ("add_agent_id_to_events", _migrate_add_agent_id),
    ("add_session_id_to_events", _migrate_add_session_id),
]


@contextmanager
def _connect():
    if not DB_PATH.exists():
        db.ensure_schema(DB_PATH, SCHEMA, events_migrations)
    conn = db.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def emit(
    source: str,
    event_type: str,
    agent_id: str | None = None,
    data: str | None = None,
    session_id: str | None = None,
):
    """Emit event to append-only log."""
    event_id = uuid7()
    event_timestamp = int(time.time())

    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (id, source, event_type, data, timestamp, agent_id, session_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, source, event_type, data, event_timestamp, agent_id, session_id),
        )
        conn.commit()


def query(source: str | None = None, agent_id: str | None = None, limit: int = 100):
    """Query events by source or agent_id."""
    if not DB_PATH.exists():
        return []

    with _connect() as conn:
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


def identify(identity: str, command: str, session_id: str | None = None):
    """Provenance: track identity invocation.

    Creates immutable audit trail linking identity → command.
    """
    constitute_identity(identity)
    agent_id = registry.ensure_agent(identity)
    emit("identity", command, agent_id, "", session_id)


def start_session(agent_id: str) -> str:
    """Start new session, auto-close any open session for this agent."""
    session_id = uuid7()

    with _connect() as conn:
        # Find any session_start events that do not have a corresponding session_end event
        open_session = conn.execute(
            """
            SELECT T1.session_id
            FROM events AS T1
            LEFT JOIN events AS T2
            ON T1.session_id = T2.session_id AND T2.event_type = 'session_end' AND T2.agent_id = ?
            WHERE T1.agent_id = ? AND T1.event_type = 'session_start' AND T2.session_id IS NULL
            ORDER BY T1.timestamp DESC LIMIT 1
            """,
            (agent_id, agent_id),
        ).fetchone()

        if open_session:
            emit("session", "session_end", agent_id, "auto_closed", open_session[0])

    emit("session", "session_start", agent_id, "", session_id)
    return session_id


def end_session(agent_id: str, session_id: str):
    """End current session."""
    emit("session", "session_end", agent_id, "", session_id)


def get_session_count(agent_id: str) -> int:
    """Count completed sessions (session_start events)."""
    with _connect() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM events WHERE agent_id = ? AND event_type = 'session_start'",
            (agent_id,),
        ).fetchone()
        return result[0] if result else 0


def get_sleep_count(agent_id: str) -> int:
    """Count sleep events for an agent."""
    with _connect() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM events WHERE agent_id = ? AND event_type = 'sleep'",
            (agent_id,),
        ).fetchone()
        return result[0] if result else 0


def get_last_sleep_time(agent_id: str) -> int | None:
    """Get timestamp of last sleep event for an agent."""
    with _connect() as conn:
        result = conn.execute(
            "SELECT timestamp FROM events WHERE agent_id = ? AND event_type = 'sleep' ORDER BY timestamp DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        return result[0] if result else None

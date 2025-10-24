import functools
import json
import sqlite3
import time
from enum import Enum
from typing import Any, Callable, TypeVar

from space.os import db
from space.os.models import Event

from .lib import paths
from .lib.identity import constitute_identity
from .lib.uuid7 import uuid7

F = TypeVar("F", bound=Callable[..., Any])

VALID_TABLES = {"events"}


class EventSource(str, Enum):
    """Valid event sources for tracking."""

    BRIDGE = "bridge"
    SPAWN = "spawn"
    CLI = "cli"
    IDENTITY = "identity"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    CONTEXT = "context"


def _validate_table(table_name: str) -> None:
    if table_name not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table_name}")


DB_PATH = paths.space_data() / "events.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    agent_id TEXT,
    event_type TEXT NOT NULL,
    data TEXT,
    timestamp INTEGER NOT NULL,
    chat_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_agent_id ON events(agent_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_event_id ON events(event_id);
"""


def _add_column_if_not_exists(
    conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str
):
    _validate_table(table_name)
    if not column_name.isidentifier() or not column_type.replace(" ", "").isidentifier():
        raise ValueError("Invalid column or type identifier")
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cursor.fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        conn.commit()


def _migrate_add_agent_id(conn: sqlite3.Connection):
    _add_column_if_not_exists(conn, "events", "agent_id", "TEXT")


def _migrate_add_chat_id(conn: sqlite3.Connection):
    _add_column_if_not_exists(conn, "events", "chat_id", "TEXT")


def _migrate_events_id_to_event_id(conn: sqlite3.Connection):
    """Rename events.id to event_id."""
    cursor = conn.execute("PRAGMA table_info(events)")
    cols = {row[1] for row in cursor.fetchall()}
    if "event_id" in cols:
        return
    conn.executescript("""
        CREATE TABLE events_new (
            event_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            agent_id TEXT,
            event_type TEXT NOT NULL,
            data TEXT,
            timestamp INTEGER NOT NULL,
            chat_id TEXT
        );
        INSERT INTO events_new SELECT id, source, agent_id, event_type, data, timestamp, session_id FROM events;
        DROP TABLE events;
        ALTER TABLE events_new RENAME TO events;
        CREATE INDEX idx_source ON events(source);
        CREATE INDEX idx_agent_id ON events(agent_id);
        CREATE INDEX idx_timestamp ON events(timestamp);
        CREATE INDEX idx_event_id ON events(event_id);
    """)


db.register("events", "events.db", SCHEMA)

db.add_migrations(
    "events",
    [
        ("add_agent_id_to_events", _migrate_add_agent_id),
        ("add_chat_id_to_events", _migrate_add_chat_id),
        ("migrate_events_id_to_event_id", _migrate_events_id_to_event_id),
    ],
)


def path():
    return DB_PATH


def emit(
    source: str,
    event_type: str,
    agent_id: str | None = None,
    data: str | None = None,
):
    """Emit event to append-only log."""
    if agent_id is not None and not isinstance(agent_id, str):
        raise ValueError(f"agent_id must be str or None, got {type(agent_id).__name__}")
    if agent_id is not None and not agent_id.strip():
        raise ValueError("agent_id must be non-empty string if provided")

    event_id = uuid7()
    event_timestamp = int(time.time())

    with db.ensure("events") as conn:
        conn.execute(
            "INSERT INTO events (event_id, source, event_type, data, timestamp, agent_id) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, source, event_type, data, event_timestamp, agent_id),
        )


def query(source: str | None = None, agent_id: str | None = None, limit: int = 100):
    """Query events by source or agent_id."""
    if not DB_PATH.exists():
        return []

    with db.ensure("events") as conn:
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
            f"SELECT event_id, source, agent_id, event_type, data, timestamp, chat_id FROM events {where_clause} ORDER BY event_id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
        return [
            Event(
                event_id=row[0],
                source=row[1],
                agent_id=row[2],
                event_type=row[3],
                data=row[4],
                timestamp=row[5],
                chat_id=row[6],
            )
            for row in rows
        ]


def identify(identity: str, command: str):
    """Provenance: track identity invocation.

    Creates immutable audit trail linking identity → command.
    """
    from space.os import spawn

    constitute_identity(identity)
    agent_id = spawn.db.ensure_agent(identity)
    emit("identity", command, agent_id, "")


def get_session_count(agent_id: str) -> int:
    """Count completed sessions (session_start events)."""
    with db.ensure("events") as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM events WHERE agent_id = ? AND event_type = 'session_start'",
            (agent_id,),
        ).fetchone()
        return result[0] if result else 0


def get_sleep_count(agent_id: str) -> int:
    """Count sleep events for an agent."""
    with db.ensure("events") as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM events WHERE agent_id = ? AND event_type = 'sleep'",
            (agent_id,),
        ).fetchone()
        return result[0] if result else 0


def get_wake_count(agent_id: str) -> int:
    """Count wake events for an agent."""
    with db.ensure("events") as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM events WHERE agent_id = ? AND event_type = 'wake'",
            (agent_id,),
        ).fetchone()
        return result[0] if result else 0


def get_last_sleep_time(agent_id: str) -> int | None:
    """Get timestamp of last sleep event for an agent."""
    with db.ensure("events") as conn:
        result = conn.execute(
            "SELECT timestamp FROM events WHERE agent_id = ? AND event_type = 'sleep' ORDER BY timestamp DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        return result[0] if result else None


def get_wakes_since_last_sleep(agent_id: str) -> int:
    """Count wake events since last sleep (in current spawn)."""
    with db.ensure("events") as conn:
        result = conn.execute(
            """SELECT COUNT(*) FROM events
               WHERE agent_id = ? AND event_type = 'wake'
               AND timestamp > COALESCE(
                   (SELECT MAX(timestamp) FROM events
                    WHERE agent_id = ? AND event_type = 'sleep'), 0)""",
            (agent_id, agent_id),
        ).fetchone()
        return result[0] if result else 0


def track(source: str) -> Callable[[F], F]:
    """Decorator: automatically emit operation events.

    Extracts function name as event_type. Emits on entry/exit.

    Usage:
        @events.track("bridge")
        def send_message(channel_id, agent_id, content):
            pass

    Emits: bridge.send_message, bridge.send_message_done (or _error on exception)
    """

    def decorator(func: F) -> F:
        event_type = func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            agent_id = kwargs.get("agent_id")

            try:
                emit(source, event_type, agent_id)
                result = func(*args, **kwargs)
                emit(source, f"{event_type}_done", agent_id)
                return result
            except Exception as e:
                emit(source, "error", agent_id, json.dumps({"op": event_type, "err": str(e)}))
                raise

        return wrapper  # type: ignore

    return decorator

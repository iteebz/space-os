import functools
import json
import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from space.lib import store

from ..lib import paths
from ..lib.uuid7 import uuid7
from .models import Event

F = TypeVar("F", bound=Callable[..., Any])

VALID_TABLES = {"events"}


class EventSource(str, Enum):
    """Valid event sources for tracking."""

    BRIDGE = "bridge"
    SPAWN = "spawn"
    CLI = "cli"
    ROLE = "role"
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


store.register("events", "events.db", SCHEMA)


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

    with store.ensure("events") as conn:
        conn.execute(
            "INSERT INTO events (event_id, source, event_type, data, timestamp, agent_id) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, source, event_type, data, event_timestamp, agent_id),
        )


def query(source: str | None = None, agent_id: str | None = None, limit: int = 100):
    """Query events by source or agent_id."""
    if not DB_PATH.exists():
        return []

    with store.ensure("events") as conn:
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

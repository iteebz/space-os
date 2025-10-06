import sqlite3
from datetime import datetime
from typing import Any
import json

from space.os.lib import uuid7
from space.os.core.storage import Repo
from space.os.core.app import SPACE_DIR # Import SPACE_DIR
from .models import Event

class EventRepo(Repo):
    def __init__(self):
        # Custom db_path for system-level events
        db_path = SPACE_DIR / "events.db"
        super().__init__("os.events", db_path=db_path) # Pass app_name and custom db_path

    def _row_to_entity(self, row: sqlite3.Row) -> Event:
        data = json.loads(row["data"]) if row["data"] else None
        metadata = json.loads(row["metadata"]) if row["metadata"] else None
        return Event(
            id=row["id"],
            timestamp=row["timestamp"],
            source=row["source"],
            event_type=row["event_type"],
            identity=row["identity"],
            data=data,
            metadata=metadata,
        )

    def add(self, event: Event) -> str:
        self._execute(
            "INSERT INTO events (id, timestamp, source, event_type, identity, data, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event.id,
                event.timestamp,
                event.source,
                event.event_type,
                event.identity,
                json.dumps(event.data) if event.data else None,
                json.dumps(event.metadata) if event.metadata else None,
            ),
        )
        return event.id

    def get(self, event_id: str) -> Event | None:
        row = self._fetch_one("SELECT * FROM events WHERE id = ?", (event_id,))
        return self._row_to_entity(row) if row else None

    def query(
        self,
        source: str | None = None,
        event_type: str | None = None,
        identity: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[Event]:
        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if source:
            query += " AND source = ?"
            params.append(source)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if identity:
            query += " AND identity = ?"
            params.append(identity)
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC"

        rows = self._fetch_all(query, tuple(params))
        return [self._row_to_entity(row) for row in rows]

    def update(self, *args, **kwargs):
        raise NotImplementedError("Event records are immutable.")

    def delete(self, event_id: str):
        self._execute("DELETE FROM events WHERE id = ?", (event_id,))

    def clear(self):
        self._execute("DELETE FROM events")
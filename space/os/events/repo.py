from datetime import datetime
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
import json
from space.os.lib import uuid7

from space.os.paths import data_for
from space.os.events.models import Event

class EventRepo:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or data_for("events")
        self.create_table()

    @contextmanager
    def get_db_connection(self, row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
        """Yield a connection to the app's dedicated database."""
        conn = sqlite3.connect(self._db_path)
        if row_factory is not None:
            conn.row_factory = row_factory
        try:
            yield conn
        finally:
            conn.close()

    def create_table(self):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    identity TEXT,
                    data TEXT,
                    timestamp INTEGER NOT NULL
                )
            """)
            conn.commit()

    def add(self, source: str, event_type: str, identity: str | None, data: dict | None):
        event_id = str(uuid7.uuid7())
        timestamp = int(datetime.now().timestamp())
        data_json = json.dumps(data) if data else None

        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO events (id, source, event_type, identity, data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, source, event_type, identity, data_json, timestamp)
            )
            conn.commit()

    def get_all(self) -> list[Event]:
        with self.get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, source, event_type, identity, data, timestamp FROM events ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            return [Event(**row) for row in rows]

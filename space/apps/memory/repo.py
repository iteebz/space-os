from pathlib import Path
from datetime import datetime
import sqlite3 # Import sqlite3

from space.os.lib import uuid7
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from space.os.paths import data_for
from .models import Memory

class MemoryRepo:
    def __init__(self):
        self._db_path = data_for("memory")

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

    def add(self, identity: str, topic: str, message: str):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            created_at = int(datetime.now().timestamp())
            cursor.execute(
                "INSERT INTO memories (uuid, identity, topic, message, created_at) VALUES (?, ?, ?, ?, ?)",
                (uuid7(), identity, topic, message, created_at),
            )
            conn.commit()

    def get_all(self) -> list[Memory]:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uuid, identity, topic, message, created_at FROM memories ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [Memory.from_row(row) for row in rows]
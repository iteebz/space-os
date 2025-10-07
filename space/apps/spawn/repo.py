from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from space.os.paths import data_for
from space.os.db.migration import apply_migrations
from space.apps.spawn.models import Identity, Constitution
from space.os.lib import uuid7

class SpawnRepo:
    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or data_for("spawn")
        self._app_root_path = Path(__file__).parent
        self.initialize()

    @contextmanager
    def _connect(self, row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
        """Yield a connection to the app's dedicated database."""
        conn = sqlite3.connect(self._db_path)
        if row_factory is not None:
            conn.row_factory = row_factory
        try:
            yield conn
        finally:
            conn.close()

    def _execute(self, sql: str, params: tuple = ()):
        with self._connect() as conn:
            conn.execute(sql, params)
            conn.commit()

    def initialize(self):
        with self._connect() as conn:
            # Ensure identities table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identities (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    current_constitution_id TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY (current_constitution_id) REFERENCES constitutions (id)
                )
            """)
            # Ensure constitutions table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS constitutions (
                    id TEXT PRIMARY KEY,
                    identity_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    change_description TEXT NOT NULL,
                    previous_version_id TEXT,
                    created_at INTEGER NOT NULL
                )
            """)
            conn.commit()

    def add_identity(self, id: str, type: str) -> Identity:
        now = int(datetime.now(timezone.utc).timestamp())
        self._execute(
            "INSERT INTO identities (id, type, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (id, type, now, now),
        )
        return self.get_identity(id)

    def get_identity(self, id: str) -> Identity | None:
        with self._connect(row_factory=sqlite3.Row) as conn:
            cursor = conn.execute("SELECT id, type, created_at, updated_at, current_constitution_id FROM identities WHERE id = ?", (id,))
            row = cursor.fetchone()
            if row:
                return Identity(**{k: row[k] for k in row.keys()}) # Explicitly convert to dict
            return None

    def add_constitution(self, name: str, version: str, content: str, identity_id: str, created_by: str, change_description: str, previous_version_id: str | None = None) -> Constitution:
        now = int(datetime.now(timezone.utc).timestamp())
        constitution_id = str(uuid7.uuid7())
        self._execute(
            "INSERT INTO constitutions (id, identity_id, name, version, content, created_by, change_description, previous_version_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (constitution_id, identity_id, name, version, content, created_by, change_description, previous_version_id, now),
        )
        return self.get_constitution_version(constitution_id)

    def get_constitution_version(self, constitution_id: str) -> Constitution | None:
        with self._connect(row_factory=sqlite3.Row) as conn:
            cursor = conn.execute("SELECT id, identity_id, name, version, content, created_by, change_description, previous_version_id, created_at FROM constitutions WHERE id = ?", (constitution_id,))
            row = cursor.fetchone()
            if row:
                return Constitution(**{k: row[k] for k in row.keys()})
            return None

    def update_identity_current_constitution(self, identity_id: str, constitution_id: str):
        now = int(datetime.now(timezone.utc).timestamp())
        self._execute(
            "UPDATE identities SET current_constitution_id = ?, updated_at = ? WHERE id = ?",
            (constitution_id, now, identity_id),
        )

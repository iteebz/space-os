from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from space.os.paths import data_for
from space.os.db.migration import apply_migrations
from space.apps.spawn.models import Identity

class SpawnRepo:
    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or data_for("spawn")
        self._app_root_path = Path(__file__).parent
        self.create_table()

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

    def create_table(self):
        with self._connect() as conn:
            migrations_dir = self._app_root_path / "migrations"
            apply_migrations("spawn", migrations_dir, conn)

    def add_identity(self, id: str, type: str) -> Identity:
        now = int(datetime.now(timezone.utc).timestamp())
        self._execute(
            "INSERT INTO identities (id, type, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (id, type, now, now),
        )
        return self.get_identity(id)

    def get_identity(self, id: str) -> Identity | None:
        with self._connect(row_factory=sqlite3.Row) as conn:
            cursor = conn.execute("SELECT id, type, current_constitution_id, created_at, updated_at FROM identities WHERE id = ?", (id,))
            row = cursor.fetchone()
            if row:
                return Identity(**row)
            return None
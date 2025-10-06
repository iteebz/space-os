from pathlib import Path
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from abc import ABC, abstractmethod

from space.os.db.migration import apply_migrations, init_migrations_table # Import the robust migration system
from space.os.lib import fs # Import fs to get root path

SPACE_DIR = fs.root() / ".space" # Define SPACE_DIR for consistent path derivation

class _StorageBase:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    @contextmanager
    def _connect(self, row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
        """Yield a connection to the database."""
        conn = sqlite3.connect(self.db_path)
        if row_factory is not None:
            conn.row_factory = row_factory
        try:
            yield conn
        finally:
            conn.close()

    def _execute(self, query: str, params: tuple = ()) -> None:
        with self._connect() as conn:
            conn.execute(query, params)
            conn.commit()

    def _fetch_one(self, query: str, params: tuple = ()) -> tuple | None:
        with self._connect() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()

    def _fetch_all(self, query: str, params: tuple = ()) -> list[tuple]:
        with self._connect() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()


class Repo(ABC, _StorageBase):
    SCHEMA_FILES: list[str] = [] # This will now represent migration file names

    def __init__(self, app_name: str):
        self._app_name = app_name
        # Derive db_path based on convention
        db_path = SPACE_DIR / "apps" / f"{app_name}.db"
        super().__init__(db_path)

        # Derive app_root_path based on convention
        # This assumes app code is in a directory named after the app within space/apps
        self._app_root_path = fs.root() / "private" / "agent-space" / "space" / "apps" / app_name
        
        self.create_table()

    def create_table(self):
        with self._connect() as conn:
            init_migrations_table(conn) # Ensure _migrations table exists
            apply_migrations(self._app_name, conn) # Apply migrations for this app

    @abstractmethod
    def add(self, *args, **kwargs):
        pass

    @abstractmethod
    def get(self, *args, **kwargs):
        pass

    @abstractmethod
    def update(self, *args, **kwargs):
        pass

    @abstractmethod
    def delete(self, *args, **kwargs):
        pass

    @abstractmethod
    def clear(self, *args, **kwargs):
        pass

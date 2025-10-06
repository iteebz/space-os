from abc import ABC
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from typing import Iterator

import os
from space.os.lib import fs

SPACE_HOME_ENV = os.getenv("SPACE_HOME")
if SPACE_HOME_ENV:
    SPACE_DIR = Path(SPACE_HOME_ENV)
else:
    # Default to .space in the project root if SPACE_HOME is not set
    SPACE_DIR = fs.root() / ".space"

class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connect(self, row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
        """Yield a connection to the database."""
        conn = sqlite3.connect(self.db_path)
        if row_factory is not None:
            conn.row_factory = row_factory
        conn.execute("PRAGMA foreign_keys = ON;") # Ensure foreign keys are enabled
        conn.execute("PRAGMA defer_foreign_keys = ON;") # Defer foreign key checks
        try:
            yield conn
        finally:
            conn.close()

class Repo(ABC, Storage):
    SCHEMA_FILES: list[str] = [] # This will now represent migration file names

    def __init__(self, app_name: str, db_path: Path | None = None):
        self._app_name = app_name
        if db_path is None:
            # Derive db_path based on convention for apps
            db_path = SPACE_DIR / "apps" / f"{app_name}.db"
        super().__init__(db_path)

        # Derive app_root_path based on convention
        # This assumes app code is in a directory named after the app within space/apps
        self._app_root_path = fs.root() / "space" / "apps" / app_name

        # Apply migrations when the Repo is initialized
        from space.os.db.migration import apply_migrations
        with self._connect() as conn:
            app_migrations_dir = self._app_root_path / "migrations"
            apply_migrations(self._app_name, app_migrations_dir, conn)

    def _execute(self, query: str, params: tuple = ()):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

    def _fetch_one(self, query: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._connect(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

    def _fetch_all(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._connect(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
from pathlib import Path
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

class Storage:
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

from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager

from space.os.db.migrations import ensure_schema as generic_ensure_schema

# Define schema files for the memory app
SCHEMA_FILES = [
    "V1__initial_schema.py",
]

def ensure_schema(conn: sqlite3.Connection, app_root_path: Path):
    """
    Ensures the memory app's database schema is up-to-date by applying migrations.
    """
    generic_ensure_schema(conn, app_root_path, SCHEMA_FILES)


@contextmanager
def connect(db_path: Path, row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the memory database."""
    conn = sqlite3.connect(db_path)
    if row_factory is not None:
        conn.row_factory = row_factory
    try:
        yield conn
    finally:
        conn.close()

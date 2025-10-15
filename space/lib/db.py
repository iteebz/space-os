import sqlite3
from pathlib import Path

from . import paths


def connect(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None  # Ensure autocommit for better test visibility
    return conn


def ensure_schema(db_path: Path, schema: str):
    with connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(schema)
        conn.commit()


def ensure_space_db(db_name: str, schema: str):
    """Return a space-scoped connection context manager with schema bootstrapped."""
    db_path = paths.dot_space() / db_name
    if not db_path.exists():
        ensure_schema(db_path, schema)
    return connect(db_path)

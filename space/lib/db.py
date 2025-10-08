import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def ensure_schema(db_path: Path, schema: str):
    with connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(schema)
        conn.commit()

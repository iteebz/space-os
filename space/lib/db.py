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


def ensure_workspace_db(db_path: Path, schema: str):
    if not db_path.exists():
        ensure_schema(db_path, schema)
    return connect(db_path)


def workspace_db_path(db_name: str) -> Path:
    """Resolve the workspace-scoped .space database path."""
    from ..spawn import config as spawn_config

    return spawn_config.workspace_root() / ".space" / db_name


def workspace_db(db_name: str, schema: str):
    """Return a workspace-scoped connection context manager with schema bootstrapped."""
    return ensure_workspace_db(workspace_db_path(db_name), schema)

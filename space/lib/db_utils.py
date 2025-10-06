from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from space.lib import fs

SPACE_DIR = fs.root() / ".space"


def database_path(name: str) -> Path:
    """Return absolute path to a database file under the workspace .space directory."""
    path = SPACE_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_database(
    name: str, initializer: Callable[[sqlite3.Connection], None] | None = None
) -> Path:
    """Create database if missing and run optional initializer inside a transaction."""
    path = database_path(name)
    with sqlite3.connect(path) as conn:
        if initializer is not None:
            initializer(conn)
        conn.commit()
    return path


@contextmanager
def connect(name: str) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the named database, creating the file if required."""
    path = database_path(name)
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()

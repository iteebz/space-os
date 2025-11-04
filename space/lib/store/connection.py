import sqlite3
import threading
from dataclasses import fields
from typing import Any, TypeVar

from space.lib import paths
from space.lib.store import migrations
from space.lib.store.sqlite import connect

T = TypeVar("T")

Row = sqlite3.Row

_DB_FILE = "space.db"
_connections = threading.local()
_migrations_loaded = False


def database_exists() -> bool:
    """Check if space.db exists at dot_space location."""
    return (paths.dot_space() / _DB_FILE).exists()


def from_row(row: dict[str, Any] | Any, dataclass_type: type[T]) -> T:
    """Convert dict-like row to dataclass instance.

    Backend-agnostic: works with sqlite3.Row, dict, or any dict-like object.
    """
    field_names = {f.name for f in fields(dataclass_type)}
    row_dict = dict(row) if not isinstance(row, dict) else row
    kwargs = {key: row_dict[key] for key in field_names if key in row_dict}
    return dataclass_type(**kwargs)


def ensure() -> sqlite3.Connection:
    """Ensure space.db exists with schema/migrations applied.

    Returns cached connection via threading.local().
    """
    global _migrations_loaded

    conn = getattr(_connections, "space", None)
    if conn is not None:
        return conn

    db_path = paths.dot_space() / _DB_FILE
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if not _migrations_loaded:
        migs = migrations.load_migrations("space.core")
        migrations.ensure_schema(db_path, migs)
        _migrations_loaded = True

    conn = connect(db_path)
    _connections.space = conn

    return conn


def close_all() -> None:
    """Close all cached connections."""
    if hasattr(_connections, "__dict__"):
        for conn in _connections.__dict__.values():
            conn.close()
        _connections.__dict__.clear()


def _reset_for_testing() -> None:
    global _migrations_loaded
    _migrations_loaded = False
    close_all()

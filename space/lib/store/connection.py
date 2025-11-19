import contextvars
import sqlite3
import threading
from dataclasses import fields
from pathlib import Path
from typing import Any, TypeVar

from space.lib import paths
from space.lib.store import migrations
from space.lib.store.sqlite import connect

T = TypeVar("T")

Row = sqlite3.Row

_DB_FILE = "space.db"
_connections = threading.local()
_migrations_loaded = threading.local()

# Context variable for test isolation - overrides paths.dot_space()
_db_path_override: contextvars.ContextVar[Path | None] = contextvars.ContextVar(
    "db_path_override", default=None
)


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
    Uses _db_path_override context var if set (for test isolation).
    """
    override = _db_path_override.get()
    if override:
        db_path = override / _DB_FILE
        cache_key = str(db_path)
    else:
        db_path = paths.dot_space() / _DB_FILE
        cache_key = "space"

    conn = getattr(_connections, cache_key, None)
    if conn is not None:
        return conn

    db_path.parent.mkdir(parents=True, exist_ok=True)

    migrations_loaded = getattr(_migrations_loaded, cache_key, False)
    if not migrations_loaded:
        migs = migrations.load_migrations("space.core")
        migrations.ensure_schema(db_path, migs)
        setattr(_migrations_loaded, cache_key, True)

    conn = connect(db_path)
    setattr(_connections, cache_key, conn)

    return conn


def close_all() -> None:
    """Close all cached connections."""
    if hasattr(_connections, "__dict__"):
        for conn in _connections.__dict__.values():
            conn.close()
        _connections.__dict__.clear()


def set_test_db_path(db_dir: Path | None) -> None:
    """Set database path override for test isolation.

    Call with path to override, None to clear.
    Propagates to worker threads via contextvars.
    """
    _db_path_override.set(db_dir)


def _reset_for_testing() -> None:
    _db_path_override.set(None)
    close_all()
    if hasattr(_migrations_loaded, "__dict__"):
        _migrations_loaded.__dict__.clear()

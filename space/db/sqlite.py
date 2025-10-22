"""SQLite storage backend implementation."""

import sqlite3
from collections.abc import Callable
from pathlib import Path

from space.lib import paths

_registry: dict[str, tuple[str, str]] = {}
_migrations: dict[str, list[tuple[str, str | Callable]]] = {}


def connect(db_path: Path) -> sqlite3.Connection:
    """Open connection to SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    return conn


def ensure_schema(
    db_path: Path,
    schema: str,
    migs: list[tuple[str, str | Callable]] | None = None,
) -> None:
    """Ensure schema exists and apply migrations."""
    with connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(schema)
        if migs:
            migrate(conn, migs)
        conn.commit()


def register(name: str, db_file: str, schema: str) -> None:
    """Register database in global registry."""
    _registry[name] = (db_file, schema)


def add_migrations(name: str, migs: list[tuple[str, str | Callable]]) -> None:
    """Register migrations for database."""
    _migrations[name] = migs


def ensure(name: str) -> sqlite3.Connection:
    """Ensure registered database exists and return connection.

    Raises ValueError if database not registered.
    """
    if name not in _registry:
        raise ValueError(f"Database '{name}' not registered. Call db.register() first.")
    db_file, schema = _registry[name]
    db_path = paths.dot_space() / db_file
    migs = _migrations.get(name)
    if not db_path.exists():
        ensure_schema(db_path, schema, migs)
    else:
        with connect(db_path) as conn:
            if migs:
                migrate(conn, migs)
    return connect(db_path)


def migrate(conn: sqlite3.Connection, migs: list[tuple[str, str | Callable]]) -> None:
    """Apply migrations to connection."""
    conn.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    conn.commit()

    for name, migration in migs:
        applied = conn.execute("SELECT 1 FROM _migrations WHERE name = ?", (name,)).fetchone()
        if applied:
            continue
        try:
            if callable(migration):
                migration(conn)
            else:
                if isinstance(migration, str) and ";" in migration:
                    conn.executescript(migration)
                else:
                    conn.execute(migration)
            conn.execute("INSERT OR IGNORE INTO _migrations (name) VALUES (?)", (name,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def registry() -> dict[str, tuple[str, str]]:
    """Return registry of all registered databases."""
    return _registry.copy()


def _reset_for_testing() -> None:
    """Reset registry and migrations state (test-only)."""
    _registry.clear()
    _migrations.clear()

import sqlite3
from collections.abc import Callable
from dataclasses import fields
from pathlib import Path
from typing import TypeVar

from . import paths

T = TypeVar("T")

_registry: dict[str, tuple[str, str]] = {}
_migrations: dict[str, list[tuple[str, str | Callable]]] = {}


def connect(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    return conn


def ensure_schema(
    db_path: Path, schema: str, migrations: list[tuple[str, str | Callable]] | None = None
):
    with connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(schema)
        if migrations:
            migrate(conn, migrations)
        conn.commit()


def register(name: str, db_file: str, schema: str):
    _registry[name] = (db_file, schema)


def migrations(name: str, migs: list[tuple[str, str | Callable]]):
    _migrations[name] = migs


def ensure(name: str):
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


def migrate(conn: sqlite3.Connection, migrations: list[tuple[str, str | Callable]]):
    conn.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    conn.commit()

    for name, migration in migrations:
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


def from_row(row: sqlite3.Row, dataclass_type: type[T]) -> T:
    """
    Converts a sqlite3.Row object to an instance of the given dataclass type.
    Matches row keys to dataclass field names.
    """
    field_names = {f.name for f in fields(dataclass_type)}
    row_dict = dict(row)
    kwargs = {key: row_dict[key] for key in field_names if key in row_dict}
    return dataclass_type(**kwargs)

"""Core store functionality - connection management."""

import sqlite3
from dataclasses import fields
from typing import Any, TypeVar

from space.lib import paths
from space.lib.store import migrations, registry
from space.lib.store.sqlite import connect

T = TypeVar("T")

Row = sqlite3.Row


def from_row(row: dict[str, Any] | Any, dataclass_type: type[T]) -> T:
    """Convert dict-like row to dataclass instance.

    Matches row keys to dataclass field names. Works with any dict-like object
    (sqlite3.Row, dict, etc.) allowing backend-agnostic conversions.
    """
    field_names = {f.name for f in fields(dataclass_type)}
    row_dict = dict(row) if not isinstance(row, dict) else row
    kwargs = {key: row_dict[key] for key in field_names if key in row_dict}
    return dataclass_type(**kwargs)


def ensure(name: str) -> sqlite3.Connection:
    """Ensure registered database exists and return connection.

    This is the main entry point - imports sqlite to establish connection.
    """
    db_file = registry.get_db_file(name)

    conn = registry.get_connection(name)
    if conn is not None:
        return conn

    db_path = paths.space_data() / db_file
    db_path.parent.mkdir(parents=True, exist_ok=True)
    migs = registry.get_migrations(name)
    migrations.ensure_schema(db_path, migs)

    conn = connect(db_path)
    registry.set_connection(name, conn)

    return conn

"""Database abstraction layer - SQLite backend with pluggable interface."""

import sqlite3

from .conversions import from_row
from .sqlite import (
    add_migrations,
    connect,
    ensure,
    ensure_schema,
    migrate,
    register,
    registry,
    resolve,
)

Row = sqlite3.Row

__all__ = [
    "connect",
    "ensure",
    "ensure_schema",
    "migrate",
    "register",
    "add_migrations",
    "registry",
    "resolve",
    "from_row",
    "Row",
]

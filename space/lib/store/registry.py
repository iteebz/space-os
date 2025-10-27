"""Database registry and lifecycle management."""

import threading
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_registry: dict[str, str] = {}
_migrations: dict[str, list[tuple[str, str | Callable]]] = {}
_connections = threading.local()


def register(name: str, db_file: str) -> None:
    """Register database in global registry.

    Args:
            name: Database identifier
            db_file: Filename for database
    """
    _registry[name] = db_file


def add_migrations(name: str, migs: list[tuple[str, str | Callable]]) -> None:
    """Register migrations for database."""
    _migrations[name] = migs


def get_db_file(name: str) -> str:
    """Get registered database filename."""
    if name not in _registry:
        raise ValueError(f"Database '{name}' not registered. Call register() first.")
    return _registry[name]


def get_migrations(name: str) -> list[tuple[str, str | Callable]] | None:
    """Get migrations for database."""
    return _migrations.get(name)


def registry() -> dict[str, str]:
    """Return registry of all registered databases."""
    return _registry.copy()


def get_connection(name: str):
    """Get cached connection for database."""
    return getattr(_connections, name, None)


def set_connection(name: str, conn) -> None:
    """Cache connection for database."""
    setattr(_connections, name, conn)


def _reset_for_testing() -> None:
    """Reset registry and migrations state (test-only)."""
    _registry.clear()
    _migrations.clear()
    if hasattr(_connections, "__dict__"):
        for conn in _connections.__dict__.values():
            conn.close()
        _connections.__dict__.clear()


def close_all() -> None:
    """Close all managed database connections."""
    if hasattr(_connections, "__dict__"):
        for conn in _connections.__dict__.values():
            conn.close()
        _connections.__dict__.clear()

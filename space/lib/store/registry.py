"""Database registry and lifecycle management."""

import threading
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_registry: dict[str, str] = {}
_migrations: dict[str, list[tuple[str, str | Callable]]] = {}
_aliases: dict[str, str] = {}
_connections = threading.local()


def _canonical(name: str) -> str:
    """Resolve registry alias to its canonical target."""
    visited: set[str] = set()
    target = name
    while target in _aliases:
        if target in visited:
            raise ValueError(f"Circular alias detected for database '{name}'")
        visited.add(target)
        target = _aliases[target]
    return target


def register(name: str, db_file: str) -> None:
    """Register database in global registry.

    Args:
            name: Database identifier
            db_file: Filename for database
    """
    canonical_name = _canonical(name)
    _registry[canonical_name] = db_file


def alias(name: str, target: str) -> None:
    """Alias database name to an existing canonical target."""
    canonical_target = _canonical(target)
    if canonical_target not in _registry:
        raise ValueError(f"Cannot alias '{name}' → '{target}': target not registered")
    _aliases[name] = canonical_target


def add_migrations(name: str, migs: list[tuple[str, str | Callable]]) -> None:
    """Register migrations for database."""
    canonical_name = _canonical(name)
    _migrations[canonical_name] = migs


def get_db_file(name: str) -> str:
    """Get registered database filename."""
    canonical_name = _canonical(name)
    if canonical_name not in _registry:
        raise ValueError(f"Database '{name}' not registered. Call register() first.")
    return _registry[canonical_name]


def get_migrations(name: str) -> list[tuple[str, str | Callable]] | None:
    """Get migrations for database."""
    canonical_name = _canonical(name)
    return _migrations.get(canonical_name)


def registry() -> dict[str, str]:
    """Return registry of all registered databases (aliases included)."""
    items = dict(_registry.items())
    for alias_name, canonical_name in _aliases.items():
        items[alias_name] = _registry.get(canonical_name, "")
    return items


def get_connection(name: str):
    """Get cached connection for database."""
    canonical_name = _canonical(name)
    return getattr(_connections, canonical_name, None)


def set_connection(name: str, conn) -> None:
    """Cache connection for database."""
    canonical_name = _canonical(name)
    setattr(_connections, canonical_name, conn)


def _reset_for_testing() -> None:
    """Reset registry and migrations state (test-only)."""
    _registry.clear()
    _migrations.clear()
    _aliases.clear()
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

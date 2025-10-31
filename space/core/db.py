"""Unified space.db database - single SQLite file with shared schema."""

from __future__ import annotations

from space.lib import migrations as migration_loader
from space.lib import paths, store

ALIASES = ("bridge", "memory", "knowledge", "spawn")
_initialized = False


def register() -> None:
    """Register unified database and configure aliases."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    store.register("space", "space.db")
    store.add_migrations("space", migration_loader.load_migrations("space.os.db"))
    for name in ALIASES:
        store.alias(name, "space")


def connect():
    """Ensure schema and return connection to unified database."""
    register()
    return store.ensure("space")


def path():
    """Return filesystem path to unified database."""
    register()
    return paths.dot_space() / "space.db"

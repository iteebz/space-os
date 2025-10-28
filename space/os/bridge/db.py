from space.lib import store
from space.os import db as unified_db

unified_db.register()


def register() -> None:
    """Legacy shim to maintain backward compatibility."""
    unified_db.register()


def connect():
    """Return connection to unified database via bridge alias."""
    return store.ensure("bridge")


def path():
    """Expose filesystem path for unified database."""
    return unified_db.path()

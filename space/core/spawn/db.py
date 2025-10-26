from space.lib import store

from . import migrations

_initialized = False


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    store.register("spawn", "spawn.db")
    store.add_migrations("spawn", migrations.MIGRATIONS)


def connect():
    """Return connection to spawn database via central registry."""
    return store.ensure("spawn")


def clear_caches() -> None:
    """Clear all spawn module caches."""
    from .api.agents import _clear_cache

    _clear_cache()

from space.lib import migrations as migration_loader
from space.lib import store

_initialized = False


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    store.register("spawn", "spawn.db")
    store.add_migrations("spawn", migration_loader.load_migrations("space.os.spawn"))


def connect():
    """Return connection to spawn database via central registry."""
    register()
    return store.ensure("spawn")

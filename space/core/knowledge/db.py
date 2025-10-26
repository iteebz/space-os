from space.lib import store

from . import migrations

_initialized = False


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    store.register("knowledge", "knowledge.db")
    store.add_migrations("knowledge", migrations.MIGRATIONS)

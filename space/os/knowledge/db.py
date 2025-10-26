from space.lib import migrations as migration_loader
from space.lib import store

_initialized = False


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    store.register("knowledge", "knowledge.db")
    store.add_migrations("knowledge", migration_loader.load_migrations("space.os.knowledge"))

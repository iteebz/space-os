import contextlib

import pytest

from space.os import config, db
from space.os.core.bridge import migrations as bridge_migrations
from space.os.core.knowledge import migrations as knowledge_migrations
from space.os.core.memory import migrations as memory_migrations
from space.os.core.spawn import migrations as spawn_migrations


@pytest.fixture(autouse=True)
def clear_config_cache():
    config.clear_cache()


@pytest.fixture
def test_space(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")
    (workspace / ".space").mkdir()

    from space.os.lib import paths

    monkeypatch.setattr(paths, "space_root", lambda base_path=None: workspace)
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: workspace / ".space")

    from space.os.db import sqlite

    monkeypatch.setattr(sqlite, "paths", paths)

    from space.os import events

    events.DB_PATH = workspace / ".space" / "events.db"

    for path in [
        workspace / ".space",
        workspace / ".space" / "bridge",
        workspace / ".space" / "security",
        workspace / ".space" / "knowledge",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    from space.os import bridge, knowledge, memory, spawn
    from space.os import config as cfg

    registry_db_path = workspace / ".space" / cfg.registry_db().name
    db.ensure_schema(
        registry_db_path,
        spawn.db.schema(),
        spawn_migrations.MIGRATIONS,
    )

    db.ensure_schema(
        workspace / ".space" / "memory.db",
        memory.db.schema(),
        memory_migrations.MIGRATIONS,
    )

    db.ensure_schema(
        workspace / ".space" / "knowledge.db",
        knowledge.db.schema(),
        knowledge_migrations.MIGRATIONS,
    )

    db.ensure_schema(
        workspace / ".space" / "bridge.db",
        bridge.db.schema(),
        bridge_migrations.MIGRATIONS,
    )

    spawn.db.clear_identity_cache()

    yield workspace

    import gc
    import sqlite3

    gc.collect()
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            with contextlib.suppress(Exception):
                obj.close()

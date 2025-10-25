import contextlib
import shutil

import pytest

from space.os import config, db
from space.os.core.bridge.migrations import MIGRATIONS as BRIDGE_MIGRATIONS
from space.os.core.knowledge.migrations import MIGRATIONS as KNOWLEDGE_MIGRATIONS
from space.os.core.memory.migrations import MIGRATIONS as MEMORY_MIGRATIONS
from space.os.core.spawn.migrations import MIGRATIONS as SPAWN_MIGRATIONS


@pytest.fixture(scope="session")
def _seed_dbs(tmp_path_factory):
    seed_dir = tmp_path_factory.mktemp("seed_dbs")

    from space.os import config as cfg
    from space.os.core.bridge import db as bridge_db
    from space.os.core.knowledge import db as knowledge_db
    from space.os.core.memory import db as memory_db
    from space.os.core.spawn import db as spawn_db

    db.ensure_schema(
        seed_dir / cfg.registry_db().name,
        spawn_db.schema(),
        SPAWN_MIGRATIONS,
    )

    db.ensure_schema(
        seed_dir / "memory.db",
        memory_db.schema(),
        MEMORY_MIGRATIONS,
    )

    db.ensure_schema(
        seed_dir / "knowledge.db",
        knowledge_db.schema(),
        KNOWLEDGE_MIGRATIONS,
    )

    db.ensure_schema(
        seed_dir / "bridge.db",
        bridge_db.schema(),
        BRIDGE_MIGRATIONS,
    )

    return seed_dir


@pytest.fixture
def test_space(monkeypatch, tmp_path, _seed_dbs):
    config.clear_cache()

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")
    (workspace / ".space").mkdir()

    from space.os.lib import paths

    monkeypatch.setattr(paths, "space_root", lambda base_path=None: workspace)
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: workspace / ".space")
    monkeypatch.setattr(paths, "space_data", lambda base_path=None: workspace / ".space")

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

    from space.os import config as cfg

    for db_name in [cfg.registry_db().name, "memory.db", "knowledge.db", "bridge.db"]:
        src = _seed_dbs / db_name
        dst = workspace / ".space" / db_name
        if src.exists():
            shutil.copy2(src, dst)
            for wal_file in [src.parent / f"{src.name}-wal", src.parent / f"{src.name}-shm"]:
                dst_wal = workspace / ".space" / wal_file.name
                if wal_file.exists():
                    shutil.copy2(wal_file, dst_wal)

    from space.os.core.spawn import db as spawn_db

    spawn_db.clear_identity_cache()

    yield workspace

    config.clear_cache()
    import gc
    import sqlite3

    gc.collect()
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            with contextlib.suppress(Exception):
                obj.close()

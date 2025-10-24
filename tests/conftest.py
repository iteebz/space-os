import contextlib
import shutil

import pytest

from space.os import config, db
from space.os.core.bridge import migrations as bridge_migrations
from space.os.core.knowledge import migrations as knowledge_migrations
from space.os.core.memory import migrations as memory_migrations
from space.os.core.spawn import migrations as spawn_migrations


@pytest.fixture(scope="session")
def _seed_dbs(tmp_path_factory):
    seed_dir = tmp_path_factory.mktemp("seed_dbs")

    from space.os import config as cfg
    from space.os.core import bridge, knowledge, memory, spawn

    db.ensure_schema(
        seed_dir / cfg.registry_db().name,
        spawn.db.schema(),
        spawn_migrations.MIGRATIONS,
    )

    db.ensure_schema(
        seed_dir / "memory.db",
        memory.db.schema(),
        memory_migrations.MIGRATIONS,
    )

    db.ensure_schema(
        seed_dir / "knowledge.db",
        knowledge.db.schema(),
        knowledge_migrations.MIGRATIONS,
    )

    db.ensure_schema(
        seed_dir / "bridge.db",
        bridge.db.schema(),
        bridge_migrations.MIGRATIONS,
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

    from space.os.core import spawn

    spawn.db.clear_identity_cache()

    yield workspace

    config.clear_cache()
    import gc
    import sqlite3

    gc.collect()
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            with contextlib.suppress(Exception):
                obj.close()

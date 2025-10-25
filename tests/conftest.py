import contextlib
import gc
import shutil
import sqlite3

import pytest

from space.os import config, db
from space.os.core import bridge as bridge_module
from space.os.core.bridge.migrations import MIGRATIONS as BRIDGE_MIGRATIONS
from space.os.core.knowledge import db as knowledge_db
from space.os.core.knowledge.migrations import MIGRATIONS as KNOWLEDGE_MIGRATIONS
from space.os.core.memory import db as memory_db
from space.os.core.memory.migrations import MIGRATIONS as MEMORY_MIGRATIONS
from space.os.core.spawn import db as spawn_db
from space.os.core.spawn.migrations import MIGRATIONS as SPAWN_MIGRATIONS
from space.os.db import sqlite as sqlite_db
from space.os.lib import paths


@pytest.fixture(scope="session")
def _seed_dbs(tmp_path_factory):
    seed_dir = tmp_path_factory.mktemp("seed_dbs")

    db.ensure_schema(
        seed_dir / config.registry_db().name,
        spawn_db.schema(),
        SPAWN_MIGRATIONS,
    )

    for db_name, schema_str, mig in [
        ("memory.db", memory_db.schema(), MEMORY_MIGRATIONS),
        ("knowledge.db", knowledge_db.schema(), KNOWLEDGE_MIGRATIONS),
        ("bridge.db", bridge_module.SCHEMA, BRIDGE_MIGRATIONS),
    ]:
        db.ensure_schema(seed_dir / db_name, schema_str, mig)

    return seed_dir


@pytest.fixture
def test_space(monkeypatch, tmp_path, _seed_dbs):
    from space.os import events

    config.clear_cache()

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")

    def paths_override(base_path=None):
        return workspace

    monkeypatch.setattr(paths, "space_root", paths_override)
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: workspace / ".space")
    monkeypatch.setattr(paths, "space_data", lambda base_path=None: workspace / ".space")
    monkeypatch.setattr(sqlite_db, "paths", paths)

    events.DB_PATH = workspace / ".space" / "events.db"

    for subdir in ["", "bridge", "security", "knowledge"]:
        (workspace / ".space" / subdir).mkdir(parents=True, exist_ok=True)

    for db_name in [config.registry_db().name, "memory.db", "knowledge.db", "bridge.db"]:
        src = _seed_dbs / db_name
        dst = workspace / ".space" / db_name
        if src.exists():
            shutil.copy2(src, dst)
            for suffix in ["-wal", "-shm"]:
                wal = src.parent / f"{src.name}{suffix}"
                if wal.exists():
                    shutil.copy2(wal, workspace / ".space" / wal.name)

    spawn_db.clear_role_cache()

    yield workspace

    config.clear_cache()
    gc.collect()
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            with contextlib.suppress(Exception):
                obj.close()

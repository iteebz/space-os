import contextlib
import gc
import shutil
import sqlite3

import pytest

from space.os import config, db
from space.os.core import bridge, knowledge, memory, spawn
from space.os.lib import paths
from space.os.lib.db import sqlite as sqlite_db


@pytest.fixture(scope="session")
def _seed_dbs(tmp_path_factory):
    seed_dir = tmp_path_factory.mktemp("seed_dbs")

    db.ensure_schema(
        seed_dir / config.registry_db().name,
        spawn.schema(),
        spawn.migrations.MIGRATIONS,
    )

    for db_name, schema_str, mig in [
        ("memory.db", memory.schema(), memory.migrations.MIGRATIONS),
        ("knowledge.db", knowledge.schema(), knowledge.migrations.MIGRATIONS),
        ("bridge.db", bridge.schema(), bridge.migrations.MIGRATIONS),
    ]:
        db.ensure_schema(seed_dir / db_name, schema_str, mig)

    return seed_dir


@pytest.fixture
def test_space(monkeypatch, tmp_path, _seed_dbs):
    from space.os import events
    from space.os.lib import chats

    monkeypatch.setattr(chats, "sync", lambda identity: None)
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

    spawn.clear_cache()

    yield workspace

    config.clear_cache()
    gc.collect()
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            with contextlib.suppress(Exception):
                obj.close()

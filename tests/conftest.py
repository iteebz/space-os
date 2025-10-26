import contextlib
import gc
import shutil
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from space import config
from space.core import bridge, knowledge, memory, spawn
from space.lib import db, paths
from space.lib.db import sqlite as sqlite_db


@pytest.fixture(scope="session")
def _seed_dbs(tmp_path_factory):
    seed_dir = tmp_path_factory.mktemp("seed_dbs")

    db.ensure_schema(
        seed_dir / config.registry_db().name,
        spawn.db.schema(),
        spawn.migrations.MIGRATIONS,
    )

    for db_module, db_name in [
        (memory.db, "memory.db"),
        (knowledge.db, "knowledge.db"),
        (bridge.db, "bridge.db"),
    ]:
        migs = {
            "memory.db": memory.migrations.MIGRATIONS,
            "knowledge.db": knowledge.migrations.MIGRATIONS,
            "bridge.db": bridge.migrations.MIGRATIONS,
        }
        db.ensure_schema(seed_dir / db_name, db_module.schema(), migs[db_name])

    return seed_dir


@pytest.fixture
def test_space(monkeypatch, tmp_path, _seed_dbs):
    from space.core import chats, events

    monkeypatch.setattr(chats, "sync", lambda identity=None, session_id=None: 0)
    config.load_config.cache_clear()
    sqlite_db.close_all()
    spawn.db.clear_caches()

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")

    def paths_override(base_path=None):
        return workspace

    monkeypatch.setattr(paths, "space_root", paths_override)
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: workspace / ".space")
    monkeypatch.setattr(paths, "space_data", lambda base_path=None: workspace / ".space")
    monkeypatch.setattr(sqlite_db, "paths", paths)

    spawn.db._initialized = False
    chats.db._initialized = False
    memory.db._initialized = False
    knowledge.db._initialized = False
    bridge.db._initialized = False

    spawn.db.register()
    chats.db.register()
    memory.db.register()
    knowledge.db.register()
    bridge.db.register()

    db.register("events", "events.db", events.SCHEMA)

    events.DB_PATH = workspace / ".space" / "events.db"

    for subdir in ["", "bridge", "knowledge"]:
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

    yield workspace

    config.load_config.cache_clear()
    spawn.db.clear_caches()
    sqlite_db.close_all()
    gc.collect()
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            with contextlib.suppress(Exception):
                obj.close()


@pytest.fixture
def mock_db():
    """Mock db.ensure context manager for unit tests."""
    mock_conn = MagicMock()
    with patch("space.lib.db.ensure") as mock_ensure:
        mock_ensure.return_value.__enter__.return_value = mock_conn
        mock_ensure.return_value.__exit__.return_value = None
        yield mock_conn


@pytest.fixture
def mock_events():
    """Mock events.emit for unit tests."""
    with patch("space.core.events.emit") as mock_emit:
        yield mock_emit


@pytest.fixture
def default_agents(test_space):
    """Registers a set of default agents for tests and returns their identities."""
    from space.core import spawn

    agents = {
        "zealot": "zealot",
        "sentinel": "sentinel",
        "crucible": "crucible",
    }
    for identity in agents:
        with contextlib.suppress(ValueError):
            spawn.register_agent(identity, f"{identity}.md", "test-model")
    return agents

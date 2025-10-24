import sqlite3

import pytest

from space.os import config, db
from space.os.knowledge import db as knowledge_db
from space.os.memory import db as memory_db
from space.os.spawn import db as spawn_db


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
    ]:
        path.mkdir(parents=True, exist_ok=True)

    from space.os import config as cfg
    from space.os.bridge import db as bridge_db

    registry_db_path = workspace / ".space" / cfg.registry_db().name
    db.ensure_schema(
        registry_db_path,
        spawn_db._SCHEMA,
        [
            ("drop_canonical_id", spawn_db._drop_canonical_id),
            ("add_pid_to_tasks", spawn_db._add_pid_to_tasks),
        ],
    )

    db.ensure_schema(
        workspace / ".space" / memory_db.MEMORY_DB_NAME,
        memory_db._MEMORY_SCHEMA,
    )

    db.ensure_schema(
        workspace / ".space" / knowledge_db.KNOWLEDGE_DB_NAME,
        knowledge_db._KNOWLEDGE_SCHEMA,
    )

    db.ensure_schema(workspace / ".space" / "bridge.db", bridge_db._SCHEMA)

    spawn_db.clear_identity_cache()

    yield workspace


@pytest.fixture
def in_memory_db(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    from space.os.bridge import db as bridge_db

    conn.executescript(spawn_db._SCHEMA)
    db.migrate(
        conn,
        [
            ("drop_canonical_id", spawn_db._drop_canonical_id),
            ("add_pid_to_tasks", spawn_db._add_pid_to_tasks),
        ],
    )
    conn.executescript(memory_db._MEMORY_SCHEMA)
    conn.executescript(knowledge_db._KNOWLEDGE_SCHEMA)
    conn.executescript(bridge_db._SCHEMA)

    monkeypatch.setattr(spawn_db, "connect", lambda: conn)

    yield conn

    conn.close()

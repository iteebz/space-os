import contextlib
import sqlite3

import pytest

from space import config
from space.knowledge import db as knowledge_db
from space.lib import db
from space.memory import db as memory_db
from space.spawn import registry

_REGISTRY_SCHEMA = """
CREATE TABLE IF NOT EXISTS constitutions (
    hash TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT,
    self_description TEXT,
    archived_at INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture(autouse=True)
def clear_config_cache():
    config.clear_cache()


@pytest.fixture
def test_space(monkeypatch, tmp_path):
    """Creates an isolated workspace for tests, with bridge and spawn initialized."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")
    (workspace / ".space").mkdir()

    from space.lib import db, paths

    monkeypatch.setattr(paths, "space_root", lambda base_path=None: workspace)
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: workspace / ".space")
    from space import events

    events.DB_PATH = workspace / ".space" / "events.db"

    for path in [
        workspace / ".space",
        workspace / ".space" / "bridge",
        workspace / ".space" / "security",
    ]:
        path.mkdir(parents=True, exist_ok=True)

        from space import config as cfg
        from space.spawn import registry

        registry_db_path = workspace / ".space" / cfg.registry_db().name
    db.ensure_schema(registry_db_path, _REGISTRY_SCHEMA, registry.spawn_migrations)

    # Initialize memory DB
    db.ensure_schema(
        workspace / ".space" / memory_db.MEMORY_DB_NAME,
        memory_db._MEMORY_SCHEMA,
        memory_db.memory_migrations,
    )

    # Initialize knowledge DB
    db.ensure_schema(
        workspace / ".space" / knowledge_db.KNOWLEDGE_DB_NAME,
        knowledge_db._KNOWLEDGE_SCHEMA,
        knowledge_db.knowledge_migrations,
    )

    # Initialize bridge DB
    from space.bridge import db as bridge_db

    db.ensure_schema(
        workspace / ".space" / "bridge.db", bridge_db._SCHEMA, bridge_db.bridge_migrations
    )

    yield workspace


@pytest.fixture
def in_memory_db():
    # Create a single in-memory connection
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Temporarily override registry.get_db to return this connection
    original_get_db = registry.get_db

    @contextlib.contextmanager
    def mock_get_db():
        yield conn

    registry.get_db = mock_get_db

    from space.bridge import db as bridge_db

    # Initialize schema for both tables on this connection
    conn.executescript(_REGISTRY_SCHEMA)
    db.migrate(conn, registry.spawn_migrations)
    conn.executescript(memory_db._MEMORY_SCHEMA)
    db.migrate(conn, memory_db.memory_migrations)
    conn.executescript(knowledge_db._KNOWLEDGE_SCHEMA)
    db.migrate(conn, knowledge_db.knowledge_migrations)
    conn.executescript(bridge_db._SCHEMA)
    db.migrate(conn, bridge_db.bridge_migrations)

    yield conn

    conn.close()
    registry.get_db = original_get_db  # Restore original

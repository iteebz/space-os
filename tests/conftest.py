import contextlib
import sqlite3
from pathlib import Path

import pytest

from space.knowledge import db as knowledge_db
from space.memory import db as memory_db
from space.spawn import registry
from space.spawn.registry import _apply_migrations

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


@pytest.fixture
def test_space(monkeypatch, tmp_path):
    """Creates an isolated workspace for tests, with bridge and spawn initialized."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")
    (workspace / ".space").mkdir()

    from space.lib import db, paths

    monkeypatch.setattr(paths, "space_root", lambda: workspace)
    monkeypatch.setattr(paths, "dot_space", lambda: workspace / ".space")
    monkeypatch.setattr(Path, "home", lambda: workspace)

    from space import events

    events.DB_PATH = workspace / ".space" / "events.db"

    for path in [
        workspace / ".space",
        workspace / ".space" / "bridge",
        workspace / ".space" / "security",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    # Directly initialize registry DB
    monkeypatch.setattr(registry.config, "registry_db", lambda: workspace / ".space" / "spawn.db")
    registry_db_path = registry.config.registry_db()
    with sqlite3.connect(registry_db_path) as conn:
        conn.executescript(_REGISTRY_SCHEMA)
        _apply_migrations(conn)
        conn.commit()

    db.ensure_schema(workspace / ".space" / memory_db.MEMORY_DB_NAME, memory_db._MEMORY_SCHEMA)
    with sqlite3.connect(workspace / ".space" / memory_db.MEMORY_DB_NAME) as conn:
        memory_db._run_migrations(conn)
    db.ensure_schema(
        workspace / ".space" / knowledge_db.KNOWLEDGE_DB_NAME, knowledge_db._KNOWLEDGE_SCHEMA
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

    # Initialize schema for both tables on this connection
    registry.init_db()
    conn.executescript(memory_db._MEMORY_SCHEMA)
    conn.executescript(knowledge_db._KNOWLEDGE_SCHEMA)

    yield conn

    conn.close()
    registry.get_db = original_get_db  # Restore original

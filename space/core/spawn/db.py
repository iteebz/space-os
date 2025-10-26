from pathlib import Path

from space.lib import db as db_lib
from space.lib import paths

from . import migrations

_initialized = False


def schema() -> str:
    return """
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    identity TEXT UNIQUE NOT NULL,
    constitution TEXT NOT NULL,
    base_agent TEXT NOT NULL,
    self_description TEXT,
    archived_at INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    channel_id TEXT,
    input TEXT NOT NULL,
    output TEXT,
    stderr TEXT,
    status TEXT DEFAULT 'pending',
    pid INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_channel ON tasks(channel_id);
"""


def path() -> Path:
    return paths.space_data() / "spawn.db"


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    db_lib.register("spawn", "spawn.db", schema())
    db_lib.add_migrations("spawn", migrations.MIGRATIONS)


def connect():
    """Return connection to spawn database via central registry."""
    return db_lib.ensure("spawn")


def clear_caches() -> None:
    """Clear all spawn module caches."""
    from .api.agents import _clear_cache

    _clear_cache()

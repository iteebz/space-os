from pathlib import Path

from space.lib import store

from . import migrations

_initialized = False


def schema() -> str:
    return """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    agent_id TEXT,
    event_type TEXT NOT NULL,
    data TEXT,
    timestamp INTEGER NOT NULL,
    chat_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_agent_id ON events(agent_id);
"""


def path() -> Path:
    from space.lib import paths

    return paths.space_data() / "events.db"


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    store.register("events", "events.db")
    store.add_migrations("events", migrations.MIGRATIONS)


def connect():
    """Return connection to events database via central registry."""
    return store.ensure("events")

from pathlib import Path

from space.lib import migrations as migration_loader
from space.lib import paths, store

_initialized = False


def schema() -> str:
    return """
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookmarks (
    agent_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    last_seen_id TEXT,
    PRIMARY KEY (agent_id, channel_id)
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    topic TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    archived_at TIMESTAMP,
    pinned_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_time ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_bookmarks ON bookmarks(agent_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_notes ON notes(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id);
"""


def path() -> Path:
    return paths.space_data() / "bridge.db"


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    store.register("bridge", "bridge.db")
    store.add_migrations("bridge", migration_loader.load_migrations("space.os.bridge"))


def connect():
    """Return connection to bridge database via central registry."""
    return store.ensure("bridge")

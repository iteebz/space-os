from pathlib import Path

from space.lib import paths, store

from . import migrations

_initialized = False


def schema() -> str:
    return """
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    archived_at INTEGER,
    core INTEGER DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'manual',
    bridge_channel TEXT,
    code_anchors TEXT,
    synthesis_note TEXT,
    supersedes TEXT,
    superseded_by TEXT
);

CREATE TABLE IF NOT EXISTS links (
    link_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    parent_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY(memory_id) REFERENCES memories(memory_id),
    FOREIGN KEY(parent_id) REFERENCES memories(memory_id),
    UNIQUE(memory_id, parent_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_memories_agent_topic ON memories(agent_id, topic);
CREATE INDEX IF NOT EXISTS idx_memories_agent_created ON memories(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_memory_id ON memories(memory_id);
CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived_at);
CREATE INDEX IF NOT EXISTS idx_memories_core ON memories(core);
CREATE INDEX IF NOT EXISTS idx_links_memory ON links(memory_id);
CREATE INDEX IF NOT EXISTS idx_links_parent ON links(parent_id);
"""


def path() -> Path:
    return paths.space_data() / "memory.db"


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    store.register("memory", "memory.db", schema())
    store.add_migrations("memory", migrations.MIGRATIONS)


def connect():
    """Return connection to memory database via central registry."""
    return store.ensure("memory")

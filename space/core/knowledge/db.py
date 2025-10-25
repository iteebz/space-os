from pathlib import Path

from space.lib import db as db_lib
from space.lib import paths

from . import migrations

_initialized = False


def schema() -> str:
    return """
CREATE TABLE IF NOT EXISTS knowledge (
    knowledge_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_agent ON knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_archived ON knowledge(archived_at);
"""


def path() -> Path:
    return paths.space_data() / "knowledge.db"


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    db_lib.register("knowledge", "knowledge.db", schema())
    db_lib.add_migrations("knowledge", migrations.MIGRATIONS)

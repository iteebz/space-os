-- 001_foundation.sql
-- Baseline schema for unified space.db covering agents, bridge, memory, and knowledge domains.
-- Separates sessions (provider-native) from spawns (space-specific invocations).

BEGIN;

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    identity TEXT NOT NULL UNIQUE,
    constitution TEXT,
    model TEXT NOT NULL,
    role TEXT,
    spawn_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_active_at TEXT,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    topic TEXT,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    archived_at TEXT,
    pinned_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    tool_count INTEGER DEFAULT 0,
    source_path TEXT,
    first_message_at TEXT,
    last_message_at TEXT
);

CREATE TABLE IF NOT EXISTS spawns (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    channel_id TEXT,
    constitution_hash TEXT,
    is_task BOOLEAN NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    pid INTEGER,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    ended_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    message TEXT NOT NULL,
    core INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge (
    knowledge_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    archived_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_created ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id);

CREATE INDEX IF NOT EXISTS idx_spawns_agent_created ON spawns(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_spawns_status ON spawns(status);
CREATE INDEX IF NOT EXISTS idx_spawns_channel_created ON spawns(channel_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_provider ON sessions(provider);

CREATE INDEX IF NOT EXISTS idx_memories_agent_created ON memories(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived_at);
CREATE INDEX IF NOT EXISTS idx_memories_core ON memories(core);

CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_agent ON knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_archived ON knowledge(archived_at);

COMMIT;

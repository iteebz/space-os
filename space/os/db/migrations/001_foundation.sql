-- 001_foundation.sql
-- Baseline schema for unified space.db covering agents, bridge, memory, and knowledge domains.
-- No legacy tables, no redundant timestamps, clean execution tracking.

BEGIN;

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    identity TEXT NOT NULL UNIQUE,
    constitution TEXT,
    model TEXT NOT NULL,
    self_description TEXT,
    spawns INTEGER NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS bookmarks (
    agent_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    session_id TEXT,
    last_seen_id TEXT,
    PRIMARY KEY (agent_id, channel_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (last_seen_id) REFERENCES messages(message_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    spawn_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    is_task BOOLEAN NOT NULL DEFAULT 0,
    constitution_hash TEXT,
    channel_id TEXT,
    pid INTEGER,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    ended_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    file_path TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    tools_used INTEGER DEFAULT 0,
    first_message_at TEXT,
    last_message_at TEXT,
    session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    topic TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    message TEXT NOT NULL,
    core INTEGER NOT NULL DEFAULT 0,
    code_anchors TEXT,
    synthesis_note TEXT,
    bridge_channel TEXT,
    supersedes TEXT,
    superseded_by TEXT,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (bridge_channel) REFERENCES channels(channel_id) ON DELETE SET NULL,
    FOREIGN KEY (supersedes) REFERENCES memories(memory_id) ON DELETE SET NULL,
    FOREIGN KEY (superseded_by) REFERENCES memories(memory_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS knowledge (
    knowledge_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    archived_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_created ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id);

CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(ended_at) WHERE ended_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_channel ON sessions(channel_id);
CREATE INDEX IF NOT EXISTS idx_sessions_is_task ON sessions(is_task);

CREATE INDEX IF NOT EXISTS idx_bookmarks_session ON bookmarks(session_id);

CREATE INDEX IF NOT EXISTS idx_chats_provider ON chats(provider);
CREATE INDEX IF NOT EXISTS idx_chats_session ON chats(session_id);

CREATE INDEX IF NOT EXISTS idx_memories_agent_created ON memories(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived_at);
CREATE INDEX IF NOT EXISTS idx_memories_core ON memories(core);

CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_agent ON knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_archived ON knowledge(archived_at);

COMMIT;

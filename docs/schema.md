# Canonical Schema – `space.db`

`space.db` is the single source of truth for agents, bridge messaging, memory, and knowledge.  
The schema lives in `space/os/db/migrations/001_foundation.sql`; the excerpt below is the canonical contract.

```sql
-- agents and lifecycle
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    identity TEXT NOT NULL UNIQUE,
    constitution TEXT,
    model TEXT NOT NULL,
    self_description TEXT,
    archived_at TEXT,
    created_at TEXT NOT NULL,
    last_active_at TEXT,
    spawn_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    spawn_number INTEGER NOT NULL,
    started_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    ended_at TEXT,
    wakes INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    channel_id TEXT REFERENCES channels(channel_id) ON DELETE SET NULL,
    input TEXT NOT NULL,
    output TEXT,
    stderr TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    pid INTEGER,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now'))
);

-- bridge (channels, messages, bookmarks)
CREATE TABLE channels (
    channel_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    topic TEXT,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    archived_at TEXT,
    pinned_at TEXT
);

CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channels(channel_id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now'))
);

CREATE TABLE bookmarks (
    agent_id TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    channel_id TEXT NOT NULL REFERENCES channels(channel_id) ON DELETE CASCADE,
    last_seen_id TEXT REFERENCES messages(message_id) ON DELETE SET NULL,
    PRIMARY KEY (agent_id, channel_id)
);

-- essential indexes
CREATE INDEX idx_messages_channel_created ON messages(channel_id, created_at);
CREATE INDEX idx_messages_agent ON messages(agent_id);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_agent ON tasks(agent_id);
CREATE INDEX idx_tasks_channel ON tasks(channel_id);
CREATE INDEX idx_sessions_agent ON sessions(agent_id);
CREATE INDEX idx_sessions_active ON sessions(ended_at) WHERE ended_at IS NULL;

-- memory
CREATE TABLE memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    core INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'manual',
    bridge_channel TEXT REFERENCES channels(channel_id) ON DELETE SET NULL,
    code_anchors TEXT,
    synthesis_note TEXT,
    supersedes TEXT REFERENCES memories(memory_id) ON DELETE SET NULL,
    superseded_by TEXT REFERENCES memories(memory_id) ON DELETE SET NULL
);

CREATE INDEX idx_memories_agent_topic ON memories(agent_id, topic);
CREATE INDEX idx_memories_agent_created ON memories(agent_id, created_at);
CREATE INDEX idx_memories_archived ON memories(archived_at);
CREATE INDEX idx_memories_core ON memories(core);

-- knowledge
CREATE TABLE knowledge (
    knowledge_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    agent_id TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    confidence REAL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    archived_at TEXT
);

CREATE INDEX idx_knowledge_domain ON knowledge(domain);
CREATE INDEX idx_knowledge_agent ON knowledge(agent_id);
CREATE INDEX idx_knowledge_archived ON knowledge(archived_at);
```

All timestamps are stored as ISO-8601 text (`datetime.now().isoformat()` compatible).  
Foreign keys are real and enforced by SQLite; cascading rules match the semantics in business logic.  
Indexes live alongside the table definitions in `001_foundation.sql` and must be kept in sync whenever the schema changes.

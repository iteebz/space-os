-- Make constitution field optional for ephemeral spawns
ALTER TABLE agents RENAME TO agents_old;

CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    identity TEXT UNIQUE NOT NULL,
    constitution TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    self_description TEXT,
    archived_at INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO agents
SELECT agent_id, identity, constitution, provider, model, self_description, archived_at, created_at, last_active_at
FROM agents_old;

DROP TABLE agents_old;

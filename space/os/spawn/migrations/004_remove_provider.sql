PRAGMA foreign_keys=OFF;

CREATE TABLE agents_new (
    agent_id TEXT PRIMARY KEY,
    identity TEXT UNIQUE NOT NULL,
    constitution TEXT,
    model TEXT NOT NULL,
    self_description TEXT,
    archived_at INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO agents_new SELECT agent_id, identity, constitution, model, self_description, archived_at, created_at, last_active_at FROM agents;

DROP TABLE agents;

ALTER TABLE agents_new RENAME TO agents;

PRAGMA foreign_keys=ON;

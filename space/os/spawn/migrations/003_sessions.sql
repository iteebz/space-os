-- Add spawn and session tracking
ALTER TABLE agents ADD COLUMN spawn_count INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN wakes_this_spawn INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    spawn_number INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    wakes INTEGER DEFAULT 0,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(ended_at) WHERE ended_at IS NULL;

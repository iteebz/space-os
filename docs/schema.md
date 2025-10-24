# Database Schema Reference

Canonical schemas for all space-os databases. Generated from source definitions in `space/os/*/db.py`.

## spawn.db

Agent registry with constitutional identity tracking.

```sql
agents (
  agent_id TEXT PRIMARY KEY,       -- UUID
  name TEXT UNIQUE,                -- identity: zealot-1, harbinger-alice
  self_description TEXT,           -- optional self-reflection
  archived_at INTEGER,             -- soft delete timestamp (null = active)
  created_at TIMESTAMP
)

constitutions (
  hash TEXT PRIMARY KEY,           -- SHA256 of constitution file
  content TEXT NOT NULL,           -- full constitution markdown
  created_at TIMESTAMP
)

tasks (
  task_id TEXT PRIMARY KEY,        -- UUID7
  agent_id TEXT NOT NULL,          -- FK to agents.agent_id
  channel_id TEXT,                 -- optional bridge channel context
  input TEXT NOT NULL,             -- task specification
  output TEXT,                     -- task result (null = pending)
  stderr TEXT,                     -- error output if failed
  status TEXT DEFAULT 'pending',   -- pending | running | completed | failed
  pid INTEGER,                     -- process ID if running
  started_at TIMESTAMP,            -- when execution began
  completed_at TIMESTAMP,          -- when execution finished
  created_at TIMESTAMP
)

Indexes:
  idx_tasks_status(status)
  idx_tasks_agent(agent_id)
  idx_tasks_channel(channel_id)
```

**Invariants:**
- Agent names are globally unique (enforced)
- Only one active agent per name (archived_at IS NULL)
- Constitutional content is immutable and content-addressed by hash
- Tasks form audit trail of agent work

## bridge.db

Async message coordination channels with unread tracking.

```sql
channels (
  channel_id TEXT PRIMARY KEY,     -- UUID
  name TEXT NOT NULL UNIQUE,       -- research, space-dev, etc.
  topic TEXT,                      -- optional channel description
  created_at TIMESTAMP,
  notes TEXT,                      -- channel metadata
  archived_at TIMESTAMP,           -- null = active
  pinned_at TIMESTAMP              -- null = unpinned
)

messages (
  message_id TEXT PRIMARY KEY,     -- UUID7
  channel_id TEXT NOT NULL,        -- FK to channels.channel_id
  agent_id TEXT NOT NULL,          -- FK to spawn.agents.agent_id
  content TEXT NOT NULL,           -- message body
  priority TEXT DEFAULT 'normal',  -- normal | alert
  created_at TIMESTAMP
)

bookmarks (
  agent_id TEXT NOT NULL,          -- FK to spawn.agents.agent_id
  channel_id TEXT NOT NULL,        -- FK to channels.channel_id
  last_seen_id TEXT,               -- last read message_id (null = unread)
  PRIMARY KEY (agent_id, channel_id)
)

notes (
  note_id TEXT PRIMARY KEY,        -- UUID7
  channel_id TEXT NOT NULL,        -- FK to channels.channel_id
  agent_id TEXT NOT NULL,          -- FK to spawn.agents.agent_id
  content TEXT NOT NULL,           -- reflection/annotation
  created_at TIMESTAMP,
  FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
)

Indexes:
  idx_messages_channel_time(channel_id, created_at)
  idx_bookmarks(agent_id, channel_id)
  idx_notes(channel_id, created_at)
  idx_messages_priority(priority)
  idx_messages_agent(agent_id)
```

**Invariants:**
- Messages are append-only (no updates/deletes)
- Bookmarks track read position per (agent, channel) pair
- Notes don't appear in message timeline (metadata only)
- Archived channels excluded from active queries
- Unread detection: `message_id > last_seen_id OR last_seen_id IS NULL`

## memory.db

Private agent context with topic sharding.

```sql
memories (
  memory_id TEXT PRIMARY KEY,      -- UUID7
  agent_id TEXT NOT NULL,          -- FK to spawn.agents.agent_id
  topic TEXT NOT NULL,             -- kebab-case: arch, safety, patterns
  message TEXT NOT NULL,           -- memory entry content
  timestamp TEXT NOT NULL,         -- formatted timestamp (YYYY-MM-DD HH:MM)
  created_at INTEGER NOT NULL,     -- unix timestamp
  archived_at INTEGER,             -- soft delete (null = active)
  core INTEGER DEFAULT 0,          -- 1 = surfaces first in context
  source TEXT DEFAULT 'manual',    -- manual | inferred | bridge | ...
  bridge_channel TEXT,             -- optional source channel_id
  code_anchors TEXT,               -- optional codebase references
  synthesis_note TEXT,             -- synthesis/supersession note
  supersedes TEXT,                 -- comma-separated memory_ids this replaces
  superseded_by TEXT               -- memory_id that replaced this
)

memory_links (
  link_id TEXT PRIMARY KEY,        -- UUID
  memory_id TEXT NOT NULL,         -- child entry
  parent_id TEXT NOT NULL,         -- parent entry
  kind TEXT NOT NULL,              -- supersedes | related | ...
  created_at INTEGER NOT NULL,
  FOREIGN KEY(memory_id) REFERENCES memories(memory_id),
  FOREIGN KEY(parent_id) REFERENCES memories(memory_id),
  UNIQUE(memory_id, parent_id, kind)
)

Indexes:
  idx_memories_agent_topic(agent_id, topic)
  idx_memories_agent_created(agent_id, created_at)
  idx_memories_memory_id(memory_id)
  idx_memories_archived(archived_at)
  idx_memories_core(core)
  idx_links_memory(memory_id)
  idx_links_parent(parent_id)
```

**Invariants:**
- Identity-scoped (agent sees only their entries)
- Topics are free-form but typically kebab-case
- Core memories surface first in wake context
- Archive instead of delete (recovery possible)
- Supersession chain tracks entry evolution

## knowledge.db

Shared domain knowledge indexed by agent + domain.

```sql
knowledge (
  knowledge_id TEXT PRIMARY KEY,   -- UUID7
  domain TEXT NOT NULL,            -- architecture, safety, coordination, ...
  agent_id TEXT NOT NULL,          -- FK to spawn.agents.agent_id (contributor)
  content TEXT NOT NULL,           -- knowledge artifact
  confidence REAL,                 -- optional 0.0-1.0 confidence score
  created_at TIMESTAMP,
  archived_at INTEGER              -- soft delete (null = active)
)

Indexes:
  idx_knowledge_domain(domain)
  idx_knowledge_agent(agent_id)
  idx_knowledge_archived(archived_at)
```

**Invariants:**
- Multi-agent write (shared truth)
- Domain taxonomy emerges organically
- Contributor provenance preserved via agent_id
- Archive instead of delete

## events.db

System-wide append-only audit log for provenance tracking.

```sql
events (
  event_id TEXT PRIMARY KEY,       -- UUID7
  source TEXT NOT NULL,            -- spawn | bridge | memory | knowledge | identity | ...
  agent_id TEXT,                   -- FK to spawn.agents.agent_id (nullable for system events)
  event_type TEXT NOT NULL,        -- agent.create | message_sent | note_add | ...
  data TEXT,                       -- event payload (free-form)
  timestamp INTEGER NOT NULL,      -- unix timestamp
  chat_id TEXT                     -- optional bridge channel_id for context
)

Indexes:
  idx_source(source)
  idx_agent_id(agent_id)
  idx_timestamp(timestamp)
  idx_event_id(event_id)
```

**Invariants:**
- Append-only (no updates/deletes)
- UUID7 provides chronological ordering
- Source identifies originating subsystem
- Agent_id links to spawn registry (nullable for system events)
- Used for: debugging, analytics, timeline reconstruction, identity audit trail

## Type System

All UUIDs are:
- **UUID7** — sortable by timestamp (used for IDs)
- **UUID4** — standard uuid (legacy, being phased out)

Timestamps:
- **TEXT TIMESTAMP** — SQLite default ISO 8601 (messages, channels, knowledge)
- **INTEGER** — unix epoch seconds (events, memories)
- **TEXT formatted** — human-readable YYYY-MM-DD HH:MM (memory.timestamp only)

## Migrations

All databases support zero-downtime migrations via the registry in `space/os/db/sqlite.py`:

1. Schema is registered at module load
2. Migrations applied on first connection (`db.ensure()`)
3. Migration state tracked in `_migrations` table per database
4. Each migration is idempotent (safe to retry)

Example migration (space/os/bridge/migrations.py):
```python
def _migrate_bridge_messages_id_to_message_id(conn):
    cursor = conn.execute("PRAGMA table_info(messages)")
    cols = {row[1] for row in cursor.fetchall()}
    if "id" not in cols:
        return
    conn.executescript("""
        CREATE TABLE messages_new (message_id TEXT PRIMARY KEY, ...);
        INSERT INTO messages_new SELECT id, ... FROM messages;
        DROP TABLE messages;
        ALTER TABLE messages_new RENAME TO messages;
    """)
```

## Storage Guarantees

**WAL mode:** All databases use `PRAGMA journal_mode=WAL` for:
- Concurrent reads during writes
- Crash recovery

**Soft deletes:** Archive instead of hard delete (`archived_at` column):
- Recovery possible
- Audit trail preserved
- Queries filter `WHERE archived_at IS NULL`

**No foreign key enforcement:** Constraints documented but not enforced in SQLite (optional feature).

**Backups:** Use `space backup` to atomically copy entire `.space/` directory.

---

See individual primitive READMEs for high-level usage and command reference.

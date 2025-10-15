# Implementation Details

Detailed reference for space-os primitives.

## Data Model

### spawn.db
```sql
agents (
  id TEXT PRIMARY KEY,      -- UUID7
  name TEXT UNIQUE,         -- agent-1, zealot-2, etc.
  role TEXT,                -- zealot, harbinger, sentinel
  channel TEXT,             -- primary coordination channel
  constitution_hash TEXT,   -- SHA256 of constitution file
  model TEXT,               -- claude-sonnet-4, etc.
  spawns INTEGER,           -- spawn counter
  created_at INTEGER
)
```

**Invariants:**
- Constitution hash must match `constitutions/<role>.md` on spawn
- Name uniqueness enforced (one agent per identity)
- Spawn counter increments on every `wake`

### bridge.db
```sql
channels (
  id TEXT PRIMARY KEY,      -- UUID7
  name TEXT UNIQUE,         -- research, architecture, etc.
  created_at TEXT,
  archived INTEGER          -- 0 or 1
)

messages (
  id TEXT PRIMARY KEY,      -- UUID7
  channel_id TEXT,          -- FK to channels.id
  agent_id TEXT,            -- FK to agents.id (spawn.db)
  sender TEXT,              -- agent name (denormalized)
  content TEXT,
  created_at TEXT
)

bookmarks (
  agent_id TEXT,            -- FK to agents.id
  channel_id TEXT,          -- FK to channels.id
  last_read_at TEXT,
  PRIMARY KEY (agent_id, channel_id)
)

notes (
  id TEXT PRIMARY KEY,      -- UUID7
  channel_id TEXT,          -- FK to channels.id
  agent_id TEXT,            -- FK to agents.id
  content TEXT,
  created_at TEXT
)
```

**Invariants:**
- Messages append-only (no updates/deletes)
- Bookmarks track read position per agent per channel
- Notes are reflections, not messages (don't appear in timeline)
- Archived channels don't show in active lists

### memory.db
```sql
memory (
  id TEXT PRIMARY KEY,      -- UUID (not UUID7)
  agent_id TEXT,            -- FK to agents.id (spawn.db)
  topic TEXT,               -- kebab-case: arch, launch-strategy, etc.
  message TEXT,
  core INTEGER,             -- 0 or 1 (core memories surface first)
  archived INTEGER,         -- 0 or 1 (soft delete)
  created_at INTEGER,
  updated_at INTEGER
)

keywords (
  entry_id TEXT,            -- FK to memory.id
  keyword TEXT,
  score REAL,               -- TF-IDF or similar
  PRIMARY KEY (entry_id, keyword)
)
```

**Invariants:**
- Identity-scoped (agent sees only their entries)
- Topic sharding for organization (no hierarchy)
- Core flag surfaces architectural/identity-defining entries
- Archive instead of delete (recovery possible)
- Keywords enable `memory inspect <id>` (find related)

### knowledge.db
```sql
knowledge (
  id TEXT PRIMARY KEY,      -- UUID7
  domain TEXT,              -- architecture, coordination, safety, etc.
  content TEXT,
  agent_id TEXT,            -- FK to agents.id (contributor)
  contributor TEXT,         -- agent name (denormalized)
  archived INTEGER,         -- 0 or 1
  created_at INTEGER,
  updated_at INTEGER
)

keywords (
  entry_id TEXT,            -- FK to knowledge.id
  keyword TEXT,
  score REAL,
  PRIMARY KEY (entry_id, keyword)
)
```

**Invariants:**
- Multi-agent writes (shared truth)
- Domain taxonomy emerges (no predefined schema)
- Contributor provenance preserved
- Keywords enable search/inspect

### events.db
```sql
events (
  id TEXT PRIMARY KEY,      -- UUID7
  source TEXT,              -- cli, bridge, spawn, memory, knowledge
  agent_id TEXT,            -- nullable (system events have no agent)
  event_type TEXT,          -- invocation, error, message_sent, etc.
  data TEXT,                -- event payload (JSON or text)
  timestamp INTEGER
)
```

**Invariants:**
- Append-only audit log
- UUID7 provides chronological ordering
- Used for debugging, analytics, context timeline
- Never deleted (archive old DBs via `space backup`)

## Data Flow

### Wake → Work → Sleep Cycle

**wake --as zealot-2:**
1. Increment spawn counter in `spawn.db`
2. Load core memories from `memory.db` (core=1)
3. Load recent memories (7d, limit 20)
4. Fetch unread message counts from `bridge.db` (via bookmarks)
5. Load recent critical knowledge (24h, decision/architecture domains)
6. Suggest priority channel (highest unread density)
7. Display context summary

**work:**
- `bridge recv <channel>` → read messages, update bookmark
- `bridge send <channel>` → append message, emit event
- `memory add` → insert entry, extract keywords
- `knowledge add` → insert entry, extract keywords
- `context "query"` → search all subsystems, return timeline + state

**sleep --as zealot-2:**
11. Prompt for session summary
12. Write summary to `memory.db` (topic: summary, core: 1)
13. Update spawn.db last_sleep timestamp

### Context Search Flow

**context "stateless" --as zealot-2:**
1. Query `events.db` WHERE data LIKE '%stateless%' AND agent_id = zealot-2
2. Query `memory.db` WHERE (message LIKE '%stateless%' OR topic LIKE '%stateless%') AND agent_id = zealot-2
3. Query `knowledge.db` WHERE content LIKE '%stateless%' OR domain LIKE '%stateless%'
4. Query `bridge.db` messages WHERE content LIKE '%stateless%'
5. Deduplicate by (content_hash, agent_id)
6. Sort by timestamp, return last 10 (evolution)
7. Return current state (top 5 per subsystem)
8. Search README.md for matching sections (lattice docs)

### Bridge Coordination Flow

**Agent A:**
```bash
bridge send research "Proposal: stateless context assembly. Thoughts?" --as zealot-1
```
1. Resolve channel ID from name
2. Insert message into `messages` table
3. Emit event: `bridge.message_sent`
4. Return success

**Agent B:**
```bash
bridge recv research --as harbinger-1
```
1. Resolve channel ID from name
2. Fetch messages WHERE channel_id = X AND created_at > last_read_at
3. Update bookmark (last_read_at = now)
4. Display messages
5. Return unread count

**Agent A (later):**
```bash
bridge notes research --as zealot-1
```
1. Prompt for reflection
2. Insert note into `notes` table
3. Emit event: `bridge.note_created`
4. Return success

## Keyword Lattice

**Purpose:** Enable `memory inspect <id>` and `knowledge inspect <id>` (find related entries via keyword similarity).

**Extraction:**
1. On insert/update, extract keywords from content (TF-IDF, stopword filter)
2. Score keywords (frequency × rarity)
3. Store top N keywords in `keywords` table

**Retrieval:**
```python
# memory inspect abc123
entry_keywords = get_keywords(entry_id="abc123")
related_entries = search_by_keywords(entry_keywords, exclude="abc123")
return sorted(related_entries, key=lambda x: x.similarity_score, limit=10)
```

**Implementation:** `space/lib/lattice.py` (keyword extraction, scoring, similarity)

## Storage Guarantees

**WAL mode:** All SQLite databases use WAL (Write-Ahead Logging) for concurrency and crash recovery.

**Atomic backups:** `space backup` copies entire `.space/` directory to `~/.space/backups/YYYYMMDD_HHMMSS/`.

**No migrations:** Schema changes handled via drop/recreate (development) or explicit migration scripts (production).

**No foreign key enforcement:** FKs documented in comments, not enforced (SQLite FK support optional).

## Testing Strategy

**Contract tests:** Validate API surface (commands, options, output format).

**Schema tests:** Validate DB schema matches expectations (tables, columns, indexes).

**Integration tests:** Validate cross-primitive flows (wake → work → sleep).

**Not tested:** UI/UX polish, edge case formatting, performance optimization.

**Coverage target:** 80% (focus on primitives, not commands).

## Performance Characteristics

**Read patterns:**
- `wake`: 3-5 queries (spawn, memory, bridge bookmarks, knowledge)
- `context`: 4-5 queries (events, memory, knowledge, bridge, README)
- `bridge recv`: 1-2 queries (messages, bookmarks)

**Write patterns:**
- `bridge send`: 2 inserts (message, event)
- `memory add`: 2 inserts (entry, keywords)
- `sleep`: 1 insert (memory summary)

**Bottlenecks:**
- Context search (4-5 LIKE queries) → acceptable for <10k entries per DB
- Keyword extraction (TF-IDF) → cached in keywords table
- Bridge inbox (unread counts) → indexed on bookmarks

**Scaling assumptions:**
- <100 agents per workspace
- <1000 memory entries per agent
- <10k knowledge entries total
- <50 active channels
- <100k messages per channel

Beyond these limits, consider partitioning or archive strategy.

## Extension Points

**New primitives:**
1. Create `space/<primitive>/` module
2. Add CLI in `<primitive>/cli.py`
3. Add entry point in `pyproject.toml`
4. Add README in `<primitive>/README.md`
5. Update main `space/README.md`

**New commands:**
1. Add function in `space/commands/<command>.py`
2. Register in `space/cli.py` via `app.command()`
3. Emit events via `space.events.emit()`

**New event types:**
1. Define in module (e.g., `bridge.message_sent`)
2. Emit via `events.emit(source, event_type, data, agent_id=None)`
3. Query via `space events` or `context`

## Constraints

**No cloud dependencies:** All data in `.space/` directory.

**No network calls:** Except Claude API for agent spawns.

**No async primitives:** SQLite is synchronous, polling model for coordination.

**No orchestration:** Agents coordinate via bridge messages, not task queues.

**No versioning:** Constitutions are immutable (hash-verified on spawn).

---

Keep it simple. Add complexity only when pain is real.

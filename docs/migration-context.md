# Schema Migration: Chats → Sessions + Spawns

## The Problem
Current schema conflates two distinct concerns:
- **Chat ingestion**: Raw provider output (Claude, Gemini, Codex) regardless of origin
- **Spawn tracking**: Space-specific agent invocations (interactive or headless)

The old `chats` table tried to hold both, creating conceptual confusion.

## The Solution
Separate into three tables:

### `sessions` (formerly `chats`)
Raw provider activity. Universal, agnostic to space.

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,    -- provider native UUID
    model TEXT NOT NULL,
    provider TEXT NOT NULL,         -- claude, gemini, codex
    file_path TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    tools_used INTEGER DEFAULT 0,
    first_message_at TEXT,
    last_message_at TEXT,
    created_at TEXT NOT NULL
);
```

Source: Provider CLI (Claude, Gemini, Codex) via `sync_provider_sessions()`.
No concept of "spawn" here. Human runs `claude`, we ingest it. Agent runs Claude, we ingest it.

### `spawns` (new)
Space-specific agent invocation context. Always has exactly one agent.

```sql
CREATE TABLE spawns (
    spawn_id TEXT PRIMARY KEY,      -- local UUID for scaffolding (~/.space/spawns/{spawn_id}/)
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,           -- pending, running, completed, failed, timeout
    is_task BOOLEAN,                -- True if headless/background, False if interactive
    channel_id TEXT,                -- None if terminal spawn, set if bridge mention spawn
    pid INTEGER,
    constitution_hash TEXT,
    session_id TEXT,                -- ALWAYS set, links to sessions.session_id
    created_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

Key insight: `spawn_id` ≠ `session_id`. Spawn is local scaffolding context. Session is provider-native UUID.

### `agents` (unchanged)
Agent registry. No changes needed.

## Spawn Types (Current + Future)

1. **Interactive spawn from terminal**
   - `spawn hailot-1` or `spawn hailot-1 "do a thing"`
   - `is_task=False`, `channel_id=NULL`
   - Always generates provider session via agent's spawn handler

2. **Headless/task spawn from terminal**
   - Future: `spawn hailot-1 --headless "task"` or similar
   - `is_task=True`, `channel_id=NULL`
   - Immediately gets session_id from Claude's `--output-format json`

3. **Bridge mention spawn (current)**
   - `@hailot-1` in bridge channel
   - `is_task=True`, `channel_id=<channel_id>`
   - Immediately gets session_id from Claude's `--output-format json`

4. **Future possibilities (deferred)**
   - Swarm spawns: `spawn hailot-swarm` (collection of agents, TBD)
   - Nested spawns: Agent A spawns Agent B (TBD)

## Migration Phases

### Phase 1: Schema (Current)
- Create new `sessions` table (copy+rename from `chats`)
- Create new `spawns` table
- Update all models (`Chat` → `Session`, etc)
- Update all queries to new table names
- Keep both tables for now (no data loss)

### Phase 2: Session Linking (Deferred)
Link `spawns.session_id` to `sessions.session_id` for all spawns:

**Headless spawns** (easy):
- `spawn_headless()` calls `claude --print --output-format json`
- Immediately parse JSON response, extract `session_id`
- Insert spawn with session_id set

**Interactive spawns** (harder):
- When spawn starts, generate `spawn_id`
- Inject bootloader message with spawn_id (e.g., "Spawn ABC123 starting")
- Filewatcher monitors provider chat dir (e.g., `~/.claude/sessions/`)
- When new session file appears (mtime <1 minute, size >0):
  - Parse file for our bootloader message with spawn_id
  - Match spawn_id to existing spawn
  - Extract `session_id` from provider file
  - Update spawn record with session_id

Time window: Check within 60 seconds of spawn creation. If no match by then, mark as orphaned (can retry later).

## Code Changes Required

### Models (`space/core/models.py`)
- Rename `Chat` → `Session`
- Update `Spawn` (if exists) or create from `Session` fields

### Migrations
- `002_sessions_and_spawns.sql`: Create new tables, populate from old, drop old

### APIs
- `space/os/spawn/api/sessions.py` → unchanged (tracks spawns now? or separate file?)
- `space/os/chats/api/sync.py` → `space/os/sessions/api/sync.py`
- `space/os/chats/api/operations.py` → `space/os/sessions/api/operations.py`
- `space/os/spawn/api/launch.py`: Update to link session_id on spawn creation (headless immediately, interactive via filewatcher)

### Tests
- Update all test fixtures, mocks, assertions to use new schema
- Add test for headless spawn → session linking
- Add test for interactive spawn → session linking (via mock filewatcher)

## Future Primitives

### Pause/Resume for Mid-Task Steering
Current model: spawn → execute → end. No interruption point.

**Better model: spawn → execute → pause → [human steers] → resume**

Enables:
- Mid-task interruption without losing context
- Single Claude session across pause/resume boundary
- Human steering with full conversation history available

Implementation sketch:
- `pause_spawn(spawn_id)`: Freeze execution, mark spawn.status='paused'
- `resume_spawn(spawn_id, new_task)`: Resume with `--resume <session_id>` + new instruction
- Session_id stays same across pause/resume (full context preserved)

Status values: pending → running → paused → running → completed/failed

This is a Phase 3+ primitive. Needs:
- Schema: Add `paused_at` field to spawns? Or just rely on status transitions?
- API: `pause_spawn()`, `resume_spawn()` functions
- Logic: Detect pause signal, capture state, resume with --resume flag
- Testing: Verify context is preserved across pause/resume boundary

## Deferred Questions

1. **Should spawns ever be created without session_id?**
   - Current answer: No. Always link immediately (headless) or defer (interactive filewatcher).
   - Alternative: Allow orphaned spawns, attempt retroactive linking later.
   - Decision: No orphans. Always link. Simplifies queries.

2. **What if filewatcher never finds the session?**
   - Spawn record exists but session_id is NULL indefinitely
   - Could mark as "session_missing" status
   - Could have async job that retries periodically
   - Decision: Deferred. Handle in Phase 3 if it becomes a problem.

3. **Multi-provider spawns?**
   - Currently one spawn = one agent = one provider
   - What if Agent can use multiple providers? (e.g., Claude for reasoning, Gemini for images)
   - Spawn should link to multiple sessions?
   - Decision: Out of scope. Current model is 1:1.

4. **Session retention policy?**
   - Sessions are immutable (read-only from provider perspective)
   - Keep forever? Archive old ones?
   - Decision: Deferred. Decide with retention policy spike.

5. **Pause/Resume implementation details?**
   - How to detect pause signal from interactive spawn? (user Ctrl+Z? explicit command?)
   - Should paused_at be tracked separately or inferred from status transitions?
   - Can we preserve agent's working directory state across pause/resume?
   - Decision: Deferred. Design as separate spike after Phase 1+2 complete.

## Progress Tracking

### Phase 1: Schema & Naming Refactoring ✅ COMPLETE

**Schema Migration:**
- [x] Updated 001_foundation.sql: sessions (provider-native) + spawns (space-specific) tables
- [x] Cleaned separation: session_id (provider UUID) vs spawn_id (local scaffolding)
- [x] Foreign key: spawns.session_id → sessions.session_id (optional initially for interactive spawns)

**Model Updates:**
- [x] Chat → Session (provider session metadata)
- [x] Created Spawn model (execution context)
- [x] ChatStats → SessionStats with total_chats → total_sessions
- [x] SpaceStats.chats → SpaceStats.sessions

**Code Refactoring:**
- [x] Renamed space/os/chats/ → space/os/sessions/
- [x] Deleted old spawn/api/sessions.py (replaced by spawns.py)
- [x] Updated all imports and function names (chat_stats() → session_stats(), etc)
- [x] Removed space/chats CLI (now standalone os/sessions primitive)
- [x] Removed backward-compatibility layer (chats_dir(), backup_chats_latest() deleted)
- [x] Deleted lib/loader.py (ProgressEvent moved to sessions/api/sync.py)
- [x] Deleted lib/sync.py (logic in sessions/api/sync.py)
- [x] Deleted chats_db() from paths.py (dead path, no longer used)
- [x] Renamed context/api/chats.py → context/api/sessions.py
- [x] Updated context API imports: chats → sessions
- [x] Updated all context test patches: chats.search → sessions.search

**Backup Restructuring:**
- [x] ~.space_backups/sessions/ mirrors ~/.space/sessions/ (additive, no /latest/ dir)
- [x] Simplified backup logic: copy files with same provider/session_id structure

**Tests & Validation:**
- [x] All 229 tests passing
- [x] No regressions
- [x] Clean cut: zero backward-compat cruft

### Deferred to Phase 2 (Session Linking)

**Session Linking Strategy:**
- Headless spawns: session_id extracted immediately from --output-format json
- Interactive spawns: Need filewatcher + bootloader injection to link session_id retroactively
  - Inject spawn_id in context message when spawn starts
  - Monitor provider session files (mtime <1 minute)
  - Match spawn_id in file content, extract session_id
  - Update spawn record with link

### Phase 2: Session Linking (Deferred)
- [ ] Headless: Update spawn_headless() to extract and link session_id
- [ ] Interactive: Implement filewatcher + bootloader injection
- [ ] Add tests for both paths
- [ ] Verify linking works end-to-end

### Phase 3: Pause/Resume Primitives (Deferred)
- [ ] Design pause_spawn() and resume_spawn() functions
- [ ] Schema: decide on paused_at field vs status-only tracking
- [ ] Integration with --resume flag in provider CLIs
- [ ] Testing: verify context preservation across pause/resume

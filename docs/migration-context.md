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

### Phase 2: Session Linking
Link `spawns.session_id` to `sessions.session_id` for all spawns. Critical for agent autonomy.

**Both paths unified:** `spawn_headless()` with `--stream-json` for headless + interactive spawns.

**Headless spawns**:
- `spawn_headless()` calls `claude --print --stream-json`
- Parse JSON stream, extract final `session_id`
- Insert spawn with session_id immediately set

**Interactive spawns**:
- Spawn created with `spawn_id` (uuid7)
- Session linking deferred (session_id remains NULL, acceptable for interactive mode)

**Linker core module:** `space/os/sessions/api/linker.py`
- `link_spawn_to_session(spawn_id, session_id)` → update DB (task spawns only)

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

### Agent Self-Reflection via Session History
With Phase 2 complete, agents can query their own execution:
```
agent> sessions <spawn_id>
# Returns full JSONL session log from that spawn
# Agent can analyze: "what did I just do?", "what worked?", "what failed?"
```

Enables:
- **Self-aware agents:** Agents read their own session logs, learn from execution
- **Agent-to-agent learning:** Agents read each other's sessions (with permissions), coordinate
- **No --resume needed:** Agents can inject session history into memory/knowledge primitives
- **Full autonomy:** 1:100 scaling—agents become self-steering via session introspection

Future: `sessions --grep <pattern> --agent <id>` for cross-agent session search.

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

### Phase 4: Bridge Integration ✅ COMPLETE

**Pause/Resume via Bridge:**
- [x] Wire `!<identity>` command to call `spawns.pause_spawn()`
- [x] Wire `@<identity>` resume detection: check for paused spawn in channel before creating fresh spawn
- [x] If paused spawn found: call `spawns.resume_spawn()` instead of fresh context assembly
- [x] Preserve full conversation context across pause/resume boundary (session_id preserved through state transition)

**Implementation:**
- Created `_parse_pause_commands()` in bridge/api/mentions.py to extract `!identity` patterns
- Created `_process_pause_commands()` to pause all running spawns for a given identity
- Updated `_process_mentions()` to:
  1. Check for paused spawns matching the identity
  2. Attempt resume if paused spawn exists
  3. Fall back to fresh spawn if resume fails (e.g., no session_id)
- All pause/resume state transitions validated via spawns API
- Session context preserved: paused → running maintains original session_id for full conversation history

**Tests:**
- `test_pause_via_bridge_command`: Verify `!identity` pauses running spawn
- `test_resume_via_bridge_mention_no_session`: Verify @mention cannot resume without session_id (graceful failure)
- `test_bridge_pause_resume_round_trip`: Full cycle pause and pause detection via bridge
- 226 tests passing (3 new bridge integration tests)

## Open Questions (Deferred)

1. **Multi-provider spawns**: Currently 1:1 (spawn → agent → provider). Future: agents spanning multiple providers?

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

### Phase 2: Session Linking ✅ COMPLETE

**Implementation:**
- Extended `Provider` protocol with `headless_session_id(output: str) -> str | None`
- All three providers extract session_id from headless output:
  - Claude: JSON response, root field `session_id`
  - Gemini: JSONL stream, first event `type: init`, field `session_id`
  - Codex: JSONL stream, first event `type: thread.started`, field `thread_id`
- Created `space/os/sessions/api/linker.py`:
  - `link_spawn_to_session(spawn_id, session_id)` → updates spawns table
  - `find_session_for_spawn(spawn_id, provider, created_at)` → for interactive fallback (deferred)
- Updated `space/os/spawn/api/launch.py`:
  - Unified headless path for all providers (Claude/Gemini/Codex)
  - Session extraction + linker integration
  - Agent-driven channel messaging (no manual posting by launcher)
- Moved Gemini JSON→JSONL conversion to provider class for cohesion
- 231 tests passing (6 linker unit tests + all integration tests)

**Key Design Decisions:**
- Session_id extracted immediately from structured output (task spawns)
- Agent-driven messaging: Agents receive channel name in bootloader context, post own results via `bridge send`
- Graceful degradation: FK constraint failures logged, session_id nullable for interactive spawns

### Phase 3: Agent Self-Reflection & Pause/Resume ✅ COMPLETE

**Agent Self-Reflection:**
- [x] Created `sessions` CLI primitive (top-level command alongside bridge, memory, context)
- [x] Commands:
  - `sessions <identity>`: List agent's recent spawns (20 most recent)
  - `sessions <spawn_id>`: Display full JSONL session log + metadata
  - `sessions sync`: Sync provider sessions to ~/.space/sessions/
- [x] Agents can introspect own execution: `sessions <spawn_id>` returns full conversation history

**Pause/Resume API:**
- [x] Added `TaskStatus.PAUSED` to core/models.py
- [x] Implemented `spawns.pause_spawn()` and `spawns.resume_spawn()`
- [x] State machine: pending → running → paused → running → completed/failed/timeout
- [x] Resume requires valid session_id (context preservation across pause boundary)
- [x] Graceful validation: prevents invalid state transitions
- [x] Tests: 7 new lifecycle tests + 6 pause/resume tests

**Code Cleanup:**
- [x] Deleted `space/os/spawn/api/tasks.py` (redundant wrapper)
- [x] Migrated all callers to `spawns.create_spawn(is_task=True)`
- [x] Renamed `update_spawn_status()` → `update_status()` (cleaner API)
- [x] Moved provider models to `space/lib/providers/MODELS` dict (removed spawn/models.py pollution)

**Tests:**
- [x] 223 tests passing (no regressions)
- [x] test_spawn_lifecycle.py: 16 tests covering all spawn lifecycle transitions
- [x] Pause/resume tests validate state machine constraints

### Phase 3.5: Constitution Isolation & Linker Refinement ✅ COMPLETE

**Constitution Isolation (Multi-Agent Safety):**
- [x] Solved critical MAS flaw: concurrent agent spawns no longer share constitution
- [x] Two-mode spawn system:
  - **Interactive spawns** (`spawn_interactive()`): Launch from `~/space/`, read CLAUDE.md via `@file` commands
  - **Task spawns** (`spawn_task()`): Launch from `~/.space/spawns/{identity}/`, isolated constitution
- [x] Per-identity constitution directories: `~/.space/spawns/{identity}/CLAUDE.md`
- [x] New `constitute()` function in spawn domain: routes constitution based on spawn mode
- [x] Task spawns get execution mode notice: "Always cd to ~/space/ first before executing commands"
- [x] No cleanup needed: identity-based scoping is persistent

**Rename to Task Terminology:**
- [x] Consistent naming with schema: `spawn_headless()` → `spawn_task()`
- [x] Provider-specific launch args: `headless_launch_args()` → `task_launch_args()`
- [x] Test file: `test_spawn_headless.py` → `test_spawn_task.py`
- [x] All CLI routing updated to explicit `spawn_task()` / `spawn_interactive()` calls

**Session Linker Elegance:**
- [x] Fixed FK constraint issue: linker now triggers `sync_provider_sessions(session_id)`
- [x] Clean solution: session record created by sync BEFORE linking (no PRAGMA tricks)
- [x] Graceful degradation: if sync fails, logs warning but spawn still created (session_id retries later)
- [x] Design aligns with Phase 2 notes: "Graceful degradation: FK constraint failures logged, session_id nullable"
- [x] Updated `link_spawn_to_session()` docstring to explain the elegant approach

**Code Organization:**
- [x] Created `space/os/spawn/api/constitute.py`: Centralized constitution writing
- [x] Moved constitution logic from lib/ to spawn domain (cleaner separation of concerns)
- [x] PROVIDER_MAP in constitute.py: Maps providers to constitution filenames (CLAUDE.md, GEMINI.md, AGENTS.md)

**Tests:**
- [x] 219 tests passing (no regressions)
- [x] test_spawn_task.py: 4 tests for task spawn execution with session linking
- [x] test_constitute.py: 4 tests for constitution setup (interactive vs headless)
- [x] test_linker.py: Updated to verify sync is called before linking
- [x] test_cli_integration.py: Fixed bridge send test to use correct callback option order

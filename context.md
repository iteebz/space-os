# Unresolved Ideas & Architecture Decisions

Placeholder for concepts with no permanent home yet. Move to proper docs once design solidifies.

## --resume Continuation Logic

**Status:** Designed, needs implementation.

**Idea:** Enable human steering via session resumption.

```
User posts in bridge:
  @zealot implement auth

System spawns with claude --print (gets session_id)
Agent executes, posts result

User responds:
  @zealot actually use approach X instead

System detects paused spawn, resumes with:
  claude --resume <session_id> --print "Use approach X"

Result: Full context preserved (original request + correction)
```

**Implementation Path:**
1. `spawns.pause_spawn(spawn_id)` — Mark as paused
2. Bridge mentions detect paused spawns, call `spawns.resume_spawn()` with `--resume` flag
3. Session_id preserved across pause→running transition
4. Already partially implemented: `pause_spawn()`, `resume_spawn()` exist in codebase

**Files to check:**
- `space/os/spawn/api/spawns.py` — pause/resume functions
- `space/os/bridge/api/mentions.py` — pause command parsing (`!identity`)

## Real-Time Observability Decisions

**Status:** Decided against stream-json parsing.

**Decision:** Resync filesystem + transcripts instead of parsing stream-json events in real-time.
- More robust than parsing streaming JSON
- Aligns with session history as source of truth
- Trades latency for simplicity

Archive: Old `spawn-context.md` had extensive stream-json parser code. Delete if needed.

## Multi-Provider Spawns

**Status:** Deferred.

**Idea:** Agent spanning multiple providers (e.g., context from Claude, execution via Gemini).

**Current:** 1:1 (spawn → agent → single provider). Future architecture TBD.

## Schema Consolidation

**Status:** Complete per Phase 1-4 of migration-context.md.

- `sessions` table: Provider-native session metadata (Claude/Gemini/Codex)
- `spawns` table: Space-specific invocation tracking (agent_id, channel_id, is_task, status)
- `spawn_id` ≠ `session_id`: Spawn is local scaffolding, Session is provider UUID

See `001_foundation.sql` for schema. Migration phases complete.

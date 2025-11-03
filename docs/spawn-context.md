# Spawn Context: Claude Code Headless Integration

**Status:** Spike completed (2025-11-04). All tests passing (229/229).

**Working Document:** This captures the complete mental model, implementation decisions, and architecture for headless agent spawning via Claude Code. Updated as work progresses.

**Reference:** spawn-patterns.md (vision), meta.md (1:100 scale), claude-spawn.md (technical details)

---

## What Was Built

**Core Implementation:**

1. **`spawn_interactive()` + `spawn_headless()` pattern** in `launch.py`:
   - `spawn_interactive(identity, extra_args)` — Traditional constitution-injected spawning (human types `spawn zealot`)
   - `spawn_headless(identity, task, channel_id)` — Direct Claude Code invocation for bridge mentions
   - Provider dispatch: currently `_spawn_headless_claude()` shipped, Gemini/Codex stubbed for future

2. **Headless Execution Pipeline:**
   - Call: `claude --print task --output-format json` with task-appropriate launch_args
   - Parse: Extract `session_id` and `result` from JSON response
   - Post: Send result to bridge channel via `messaging.send_message()`
   - Track: Task lifecycle (create_task → start_task → complete_task/fail_task)

3. **Stream-JSON Parsing Foundation** (`trace/api/stream_parser.py`):
   - Parses stream-json events from Claude Code (`--output-format stream-json --verbose`)
   - Yields structured events: system_init, tool_call, tool_result, text, completion
   - Ready for real-time observability integration (deferred)

4. **Bridge Integration** (`mentions.py`):
   - Removed unnecessary constitution injection
   - Simplified spawn flow: parse mentions → `spawn_headless()` → done
   - Async, non-blocking execution (threaded)

5. **Session Management Enhancement**:
   - `sessions.py` now accepts explicit `session_id` parameter
   - Allows storing Claude Code's native UUIDs directly (no mapping needed)

**Tests:** 
- 4 new integration tests (test_spawn_headless.py), all passing
- Full suite: 229/229 passing

---

## Problems Solved

1. **Invisibility → Foundation for Observability:** Stream-json parser is ready. Next: integrate into trace CLI to show live tool calls as agents execute.

2. **Interruption → Sequential Invoke-Respond Cycles:** Not solved yet. Current pattern: agent spawns, posts result to bridge. Human responds in channel. Agent reads response on next spawn via `--resume`. Steering possible, not yet automated.

3. **Continuity → Context Assembled at Spawn:** Implemented. Each spawn reads full bridge + memory history. Token cost is frontloaded (one context assembly per spawn) but manageable.

4. **Schema Mess → Deferred:** Session/Chat consolidation not yet done. For now: use Claude's session_id directly as our session_id. No mapping layer needed.

---

## Key Discoveries & Technical Insights

### 1. Claude Code --print is Headless-Friendly

```bash
claude --print "task" --output-format json
# Returns: {"session_id": "...", "result": "...", ...}
# Exits immediately. Non-interactive.
```

This is the foundation. Agents can invoke Claude Code and get structured output.

### 2. Session IDs from Claude Code are Globally Unique

Claude Code generates UUIDs (uuid4 or similar) for each session. These are guaranteed unique.

**Decision:** Use Claude's session_id directly as our session_id, not generating our own. This eliminates the chat_id vs session_id confusion.

### 3. Stream-JSON Enables Real-Time Observability

```bash
echo "task" | claude --input-format text --output-format stream-json --verbose
# Outputs: One JSON object per line
# Types: system, assistant, user, result
```

Each line is a complete event. Example:
```json
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"...","name":"Bash","input":{...}}]}}
{"type":"user","message":{"content":[{"tool_use_id":"...","type":"tool_result","content":"..."}]}}
{"type":"result","subtype":"success","session_id":"...","result":"..."}
```

This gives you **full visibility into agent execution** (tool calls, results, reasoning) in real-time.

### 4. Session Continuation via --resume Enables Steering

```bash
claude --resume <session_id> --print "Continue with this correction" --output-format json
# Restores full conversation history
# Agent reads your new direction and continues
```

Combined with bridge messages, agents can:
1. Spawn and execute (`claude --print task --output-format stream-json`)
2. Post key events to bridge (tool calls, completion)
3. Check bridge for human corrections
4. Resume with new direction (`claude --resume <session_id>`)

This is **invoke-respond-invoke** pattern. No polling, no background tasks.

---

## Current Architecture: Spawn → Post → Respond → Resume

```
┌─ Human posts in bridge
│  @zealot implement auth in #backend
└─────────────────────────────────────────────
           ↓
┌─ mentions.py detects @zealot
│  1. create_task(zealot, channel_id)
│  2. start_task()
│  3. spawn_headless(zealot, task, channel_id)
└─────────────────────────────────────────────
           ↓
┌─ launch.py executes headless
│  1. claude --print task --output-format json
│  2. Extract session_id from JSON response
│  3. Parse result field
│  4. messaging.send_message(channel, zealot, result)
│  5. complete_task()
└─────────────────────────────────────────────
           ↓
┌─ Result posted to bridge
│  ✓ zealot: [implementation result]
└─────────────────────────────────────────────
           ↓
┌─ Human responds (NOT YET AUTOMATED)
│  @zealot actually use approach X instead
│  (This gets stored in bridge channel)
└─────────────────────────────────────────────
           ↓
┌─ Future: Agent reads correction
│  spawn_headless(zealot, ...) called again
│  claude --resume <session_id> --print "Use approach X"
│  Claude reads full history including correction
│  Responds with revised implementation
└─────────────────────────────────────────────
```

**Current State:**
- ✓ Headless spawning works (claude --print)
- ✓ Session tracking (session_id stored)
- ✓ Bridge posting (results visible to human)
- ✗ Automated interruption (manual for now)
- ✗ Real-time observability (stream-json parser ready, not integrated)
- ✗ `--resume` continuation (logic proven, not coded)

**Key Properties:**
- Minimal orchestration (mention → spawn → post → done)
- Human-visible results (bridge channel)
- Future-proof for steering (session_id preserved, --resume ready)
- Token-efficient (context assembled at spawn time, not streamed)

---

## Scope & Deferred Work

**Not Yet Implemented (Future Spikes):**

1. **`--resume` Continuation:** Logic proven, code not yet written. Enables steering by having agents re-invoke with `--resume <session_id>` + new direction.

2. **Stream-JSON Integration:** Parser exists, but not integrated with trace CLI. Next: real-time tool call visibility in council/trace.

3. **Automated Steering:** Humans must manually post corrections to bridge. Could automate: detect human response → trigger agent to resume with correction.

4. **Schema Consolidation:** Sessions and Chats tables are still separate. Deferred until after MVP works. Plan: use Claude's session_id as primary key, remove mapping layer.

5. **Gemini/Codex Headless:** Stubbed as `NotImplementedError`. Add when providers have equivalent `--print --output-format json` support.

6. **Live Tracing:** Stream-json events could be posted to bridge in real-time. Currently just stored in Claude's local JSONL. Low priority unless observability becomes blocking.

---

## File Changes Summary

**Modified:**
- `space/os/spawn/api/sessions.py` — Added optional `session_id` parameter to `create_session()`
- `space/os/spawn/api/launch.py` — Refactored into `spawn_interactive()` + `spawn_headless()`, added provider dispatch
- `space/os/bridge/api/mentions.py` — Removed unused constitution logic, simplified to use `spawn_headless()`

**Created:**
- `space/trace/api/stream_parser.py` — Parse stream-json events from Claude Code
- `tests/integration/test_spawn_headless.py` — Integration tests (4/4 passing)
- `docs/claude-spawn.md` — Technical reference (session ID extraction, stream-json structure)
- `docs/spawn-context.md` — This document (mental model + architecture)

**Status:** All 229 tests passing. No regressions.

---

## For Tomorrow: What Hailot Needs to Know

1. **Entry Point:** Bridge mentions trigger `spawn_headless()`. When a human posts `@zealot do X`, the system:
   - Parses the mention
   - Creates a task session
   - Calls `spawn_headless(zealot, "do X", channel_id)`
   - Waits for result
   - Posts to bridge

2. **Session Tracking:** Claude Code's UUID is stored directly in our sessions table. No mapping needed.

3. **Stream-JSON Ready:** `parse_stream_json()` in `trace/api/` can extract tool calls, results, reasoning. Not yet integrated with trace CLI or council.

4. **Next Big Feature:** `--resume` continuation. Pattern:
   - Human posts correction in bridge
   - Some orchestration logic detects it
   - Calls `spawn_headless()` again
   - Claude Code resumes with `--resume <session_id> --print "new direction"`
   - Full context preserved (including original request + correction)

5. **Deferred:** Live tracing, schema consolidation, Gemini/Codex support, automated steering detection.

---

## Why This Matters (The Vision)

This implements the core of spawn-patterns.md:
- **Stateless agents** reading from shared context (bridge + memory)
- **Ephemeral spawning** with **session continuity** via provider's native state
- **Human steering** via conversation (bridge messages)
- **Observability ready** (stream-json parser exists, waiting for integration)

At 1:100 scale, you're not orchestrating 100 agents. You're steering via constitutional multiplicity (zealot, sentinel, etc) reading and responding in bridge channels. This architecture makes that possible.

---

## Open Questions

1. **Cost analysis:** Token usage at scale (each spawn = fresh context assembly). Compare to session persistence.
2. **Context window:** Bridge history eventually exceeds Claude's window. Archive + search strategy?
3. **Swarm coordination:** When agent spawns N workers, how do they signal completion? Timeout vs. explicit "done" messages?
4. **Nested depth:** Can workers spawn sub-workers? What's the limit?
5. **Trace storage:** Stream-json in `~/.claude/projects/` is authoritative. Replicate to space.db for queries?

---

## Quick Reference

**Key Functions:**
- `spawn_interactive(identity, extra_args)` — Constitution-injected spawn (human-driven)
- `spawn_headless(identity, task, channel_id)` — Direct Claude invocation (bridge-driven)
- `_spawn_headless_claude(agent, task, session, channel_id)` — Claude-specific implementation
- `parse_stream_json(stream)` — Parse stream-json events (ready for integration)

**Key Files:**
- `launch.py` — Spawn orchestration
- `mentions.py` — Bridge trigger logic
- `stream_parser.py` — Event parsing foundation
- `claude-spawn.md` — Technical details
- `spawn-patterns.md` — Vision document
- `meta.md` — 1:100 context

# Architecture

High-level design of space-os primitives and data flows.

## Overview

**Seven primitives, single database, zero orchestration.**

Agents coordinate asynchronously via message passing (bridge), maintain private working context (memory), build shared discoveries (knowledge), claim work from a shared ledger (task), search across all subsystems (context), and execute via constitutional identity (spawn). Constitutional identity provides the agent registry with immutable provenance.

**Design principle:** No central orchestration. Agents are fully autonomous. Coordination emerges through shared communication channels and collective knowledge.

## Data Hierarchy

```
context    — unified search (query primitive)
  ↓
task       — shared work ledger (prevents duplication at scale)
  ↓
knowledge  — shared truth (multi-agent writes)
  ↓
memory     — working state (single-agent writes)
  ↓
bridge     — ephemeral coordination (conversation until consensus)
  ↓
spawn      — identity registry (constitutional provenance)
```

Pattern: Bridge → Memory → Knowledge (information flows "down" as consensus solidifies)

## Primitives

For detailed information and CLI reference:

- [Spawn](spawn.md) — agent registry, constitutional identity, task/spawn tracking
- [Bridge](bridge.md) — async coordination channels (append-only, bookmarks)
- [Memory](memory.md) — private working context (identity-scoped, topic-sharded)
- [Knowledge](knowledge.md) — shared discoveries (domain-indexed, immutable)
- [Task](task.md) — shared work ledger (project-scoped, agent-claimable)
- [Sessions](sessions.md) — provider-native chat history (Claude, Gemini, Codex)
- [Context](context.md) — unified query primitive (search across all primitives, no dedicated storage)

## Execution Patterns

**Direct spawn** — Run agent by registered identity:
```bash
zealot-1 "task"
```

**@mention spawn** — Message with @identity triggers agent:
```bash
bridge send channel "@zealot-1 analyze proposal" --as you
# System builds prompt from channel context, spawns agent, posts reply
```

**Task tracking** — Create, monitor, kill tasks:
```bash
spawn tasks
spawn logs <task-id>
```

**Session ingestion** — Discover and sync from providers:
```bash
sessions sync         # claude/gemini/codex sessions
```

## Storage

**Single database:** `.space/space.db` (SQLite)

Each primitive owns its schema (see table definitions in primitive docs). Canonical full schema: `space/core/migrations/001_foundation.sql`

## Coordination Flow

1. **Send** — Agent A posts message to channel
   - `bridge.send(channel_id, agent_id, "message")`
   - Message appended (immutable)
   
2. **Read** — Agent B reads unread messages
   - `bridge.recv(channel_id, agent_id)`
   - Bookmark updated (last_seen_id)
   - @mentions extracted, agents spawned if present

3. **Consolidate** — Insights move down the hierarchy
   - Bridge → ephemeral discussion
   - Memory → working notes (if single agent)
   - Knowledge → shared discovery (if consensus reached)

# Architecture

High-level design of space-os primitives and data flows.

## Overview

**Five primitives, single database, zero orchestration.**

Agents coordinate asynchronously via message passing (bridge), maintain private working context (memory), build shared discoveries (knowledge), and search across all subsystems (context). Constitutional identity (spawn) provides the agent registry with immutable provenance.

**Design principle:** No central orchestration. Agents are fully autonomous. Coordination emerges through shared communication channels and collective knowledge.

## Data Hierarchy

```
context    — unified search (read-only meta-layer)
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

- [Spawn](spawn.md) — agent registry, constitutional identity, task tracking
- [Bridge](bridge.md) — async coordination channels (append-only, bookmarks)
- [Memory](memory.md) — private working context (identity-scoped, topic-sharded)
- [Knowledge](knowledge.md) — shared discoveries (domain-indexed, immutable)
- `context` — unified search across all subsystems (no dedicated storage)

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

**Chat ingestion** — Discover and sync from providers:
```bash
space chats sync         # claude/gemini/codex chats
```

## Storage

**Single database:** `.space/space.db` (SQLite)

Schema includes:
- `agents` — identity, model, constitution, provider
- `channels`, `messages`, `bookmarks` — async coordination
- `memories`, `links` — private context
- `knowledge` — shared discoveries
- `tasks`, `sessions` — execution tracking

See [docs/schema.md](schema.md) for full schema.

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

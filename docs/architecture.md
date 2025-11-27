# Architecture

High-level design of space-os primitives and data flows.

## Overview

**Coordination substrate for existing agent CLIs (Claude Code, Gemini CLI, Codex).**

**space-os does not invoke LLMs.** It provides message routing infrastructure for agent CLIs that already exist. Think: Unix pipes for AI agents.

Seven coordination primitives, single database (`space.db`), message-based coordination.

**Design principle:** Message passing, not orchestration. Agents are fully autonomous. Coordination emerges through shared communication channels and collective knowledge.

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
bridge     — async coordination (conversation until consensus)
  ↓
spawn      — identity registry (constitutional provenance)
```

Pattern: Bridge → Memory → Knowledge (information flows down as consensus solidifies)

## Primitives

- [Spawn](spawn.md) — agent registry, constitutional identity, spawn tracking
- [Bridge](bridge.md) — async coordination channels, handoffs
- [Memory](memory.md) — private working context
- [Knowledge](knowledge.md) — shared discoveries
- [Task](task.md) — shared work ledger
- [Sessions](sessions.md) — provider chat history
- [Context](context.md) — unified search
- [Constitutions](constitutions.md) — identity injection

## Execution

**@mention spawn:**
```bash
bridge send research "@zealot-1 analyze proposal" --as tyson
# System builds prompt from channel context + constitution, spawns agent, posts reply
```

**Spawn tracking:**
```bash
spawn list                    # list spawns
spawn logs <spawn-id>         # view session output
spawn abort <spawn-id>        # terminate
```

**Session sync:**
```bash
sessions sync                 # discover provider sessions
```

## Storage

**Single database:** `.space/space.db` (SQLite)

Each primitive owns its schema. See table definitions in primitive docs.

## Coordination Flow

1. **Send** — Agent posts message to channel
   - Message appended (immutable)
   - @mentions trigger spawns
   
2. **Read** — Agent reads channel
   - Bookmark updated
   - Context injected at spawn time

3. **Consolidate** — Insights flow down hierarchy
   - Bridge → discussion
   - Memory → working notes
   - Knowledge → shared discovery

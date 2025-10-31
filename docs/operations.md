# Operations Guide

Quick reference for running space-os agents. For detailed command options, use `<command> --help`.

## Quick Start

```bash
# Initialize workspace
space init

# Register agent with constitutional identity
spawn register zealot zealot-1 --model claude-sonnet-4

# Run agent directly (dynamic CLI command)
zealot-1 "your task or question"

# Coordinate through bridge (async messaging)
bridge send research "proposal for review" --as zealot-1
bridge recv research --as zealot-1

# Store private context
memory add --as zealot-1 --topic tasks "completed X, next is Y"

# Contribute shared discovery
knowledge add --domain architecture --as zealot-1 "key insight about system"

# Search across all subsystems
context search "query terms" --as zealot-1
```

## Spawn Patterns

**Direct spawn** — Run by identity:
```bash
zealot-1 "your task"
```

**@mention spawn** — Bridge triggers agent:
```bash
bridge send channel "@zealot-1 analyze proposal" --as you
# System spawns zealot-1 with channel context, posts reply
```

**Task tracking**:
```bash
spawn tasks              # list all tasks
spawn logs <task-id>     # view task input/output/stderr
spawn kill <task-id>     # stop running task
```

**Chat ingestion** — Sync from providers:
```bash
space chats sync         # discover claude/gemini/codex chats
space chats --stats      # view statistics by provider
```

## Primitives

Detailed documentation for each primitive:

- [Spawn](spawn.md) — agent registry, constitutional identity, task tracking
- [Bridge](bridge.md) — async coordination channels
- [Memory](memory.md) — private working context
- [Knowledge](knowledge.md) — shared discoveries
- `context` — unified search (no storage, meta-layer)

## Storage & Backup

**Atomic backups:**
```bash
space backup  # copies entire .space/ to timestamped backup
```

**Database location:**
- `.space/space.db` — unified schema (agents, channels, messages, bookmarks, memories, links, knowledge, tasks, sessions)

## Common Operations

**View agent status:**
```bash
spawn list           # all active agents
spawn list --archived  # including archived agents
space health         # validate DB schemas
```

**Search and introspect:**
```bash
context search "query"   # memory + knowledge + bridge + canon
memory list --as <identity>
knowledge query --domain <domain>
bridge channels          # list active and archived channels
```

**Manage agents:**
```bash
spawn rename <old-identity> <new-identity>
spawn clone <identity> <new-identity>
spawn merge <source-identity> <target-identity>
```

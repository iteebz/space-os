# space-os

Constitutional cognitive infrastructure for multi-agent coordination.

## What

Infrastructure primitives enabling autonomous agent coordination with constitutional identity. Agents persist context across deaths, coordinate asynchronously, and build shared knowledge without orchestration.

Five primitives, single database (`space.db`), zero orchestration.

## Design

**Data hierarchy:**
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

**Storage:** `.space/` directory (workspace-local)
```
.space/
├── space.db       # unified schema (agents, channels, messages, memories, knowledge, spawns, sessions)
├── spawns/…       # per-identity constitution (isolated per spawn)
└── sessions/…     # synced provider chat files (Claude, Gemini, Codex)
```

**Principles:**
- Composable primitives over monolithic frameworks
- Workspace sovereignty (no cloud dependencies)
- Async-first coordination (polling, not orchestration)
- Constitutional identity optional (spawn layer)
- Filesystem as source of truth

See [docs/architecture.md](docs/architecture.md) for design details.

## Spawn Patterns

**Direct spawn** — Run agent by identity:
```bash
spawn register zealot zealot-1 --model claude-sonnet-4
zealot-1 "your task here"  # dynamic CLI from space CLI
```

**@mention spawn** — Message triggers agent:
```bash
bridge send research "@zealot-1 analyze this proposal" --as you
# System spawns zealot-1, builds prompt from channel context, posts reply
```

**Task-based spawn** — Create task, agent executes:
```bash
spawn tasks
spawn logs <spawn-id>      # track execution
spawn kill <spawn-id>      # stop running task
```

**Session ingestion** — Discover and sync from providers:
```bash
sessions sync           # discover claude/gemini/codex sessions
sessions <spawn-id>     # view full session transcript
```

## Core Workflows

**Coordinate asynchronously:**
```bash
# Send message to channel
bridge send research "proposal for review" --as zealot-1

# Read unread channels
bridge inbox --as zealot-1

# Unified context search (memory + knowledge + bridge + canon)
context search "your query" --as zealot-1
```

**Manage memory and knowledge:**
```bash
# Private working context (agent-specific)
memory add --as zealot-1 --topic arch "core insight"
memory list --as zealot-1

# Shared discoveries (multi-agent, domain-indexed)
knowledge add --domain architecture --as zealot-1 "shared discovery"
knowledge query --domain architecture
```

## CLI Reference

Run `<command> --help` for full options. Each primitive is first-class:
- `spawn` — agent registry, task tracking
- `bridge` — async channels, messages, coordination
- `memory` — private working context
- `knowledge` — shared discoveries
- `context` — unified search (memory + knowledge + bridge + canon)
- `space` — orchestrator (init, health, stats, backup)
- `canon` — git-backed immutable docs
- `council` — live channel streaming
- `daemons` — background upkeep tasks

## Development

```bash
poetry install                              # includes dev dependencies
poetry run pytest                           # run tests
poetry run ruff format .                    # format
poetry run ruff check . --fix               # lint + fix
```

## Philosophy

**Cognitive multiplicity over task automation.** Constitutional identities as frames, not workers. Humans conduct multiple perspectives simultaneously.

**Primitives over platforms.** Composable layers that combine into coordination substrate, not monolithic framework.

**Workspace sovereignty.** All data local in `.space/`. Full control over cognitive infrastructure.

**Async-first.** Agents coordinate via conversation until consensus. No orchestration, no task queues.

---

> context is all you need

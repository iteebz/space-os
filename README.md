# space-os

Coordination substrate for existing agent CLIs.

## Not an Agent Framework

**space-os does not invoke LLMs.** It provides coordination primitives for agent CLIs that already exist:
- Claude Code (`claude-code`)
- Gemini CLI (`gemini-cli`)
- Codex CLI (`codex`)

**Think: Unix pipes for AI agents.** Pipes (`|`) don't execute programs—they connect them. Bridge channels don't spawn LLM loops—they route messages between constitutional agents.

**Every other multi-agent framework reimplements the agent loop** (LLM + tools + memory). We're saying: "Agent CLIs already exist. Let's connect them via message passing."

**Interoperability:** Claude agents message Gemini agents message Codex agents—all reading the same `space.db`.

## What

Seven coordination primitives, single database (`space.db`), message-based coordination.

**Human interface:** See [space-cmd](https://github.com/teebz/space-cmd) for the TUI command center (observability + steering).

## Design

**Data hierarchy:**
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

**Storage:** `.space/` directory (workspace-local)
```
.space/
├── space.db       # unified schema (agents, channels, messages, memories, knowledge, tasks, spawns, sessions)
├── spawns/…       # per-identity constitution (isolated per spawn)
└── sessions/…     # synced provider chat files (Claude, Gemini, Codex)
```

**Principles:**
- Coordination substrate, not agent framework (connects existing agent CLIs)
- Composable primitives over monolithic frameworks
- Workspace sovereignty (no cloud dependencies)
- Message passing, not orchestration (agents coordinate via conversation)
- Constitutional identity as routing primitive (spawn layer)
- Filesystem as source of truth

See [docs/architecture.md](docs/architecture.md) for design details, [canon/metaspace/cli-pattern.md](/Users/teebz/space/canon/metaspace/cli-pattern.md) for CLI context injection, [canon/metaspace/spawn-patterns.md](/Users/teebz/space/canon/metaspace/spawn-patterns.md) for ephemeral agent coordination.

## Spawn Patterns

**Direct spawn** — Run existing agent CLI by constitutional identity:
```bash
spawn register zealot zealot-1 --model claude-sonnet-4
zealot-1 "your task here"  # invokes claude-code with identity + channel context
```

**@mention spawn** — Message triggers agent CLI invocation:
```bash
bridge send research "@zealot-1 analyze this proposal" --as you
# System invokes zealot-1's agent CLI, injects channel context, posts reply to bridge
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

Run `<command> --help` for full options.

**Primitives:**
- `spawn` — agent registry, constitutional identity, tracing, task tracking
- `bridge` — async channels, messages, coordination
- `memory` — private working context
- `knowledge` — shared discoveries
- `task` — shared work ledger, project-scoped coordination
- `context` — unified search across all primitives
- `sessions` — query and sync provider chat history (Claude, Gemini, Codex)

**Utilities:**
- `space` — workspace management (init, health, stats, backup)
- `daemons` — background upkeep tasks

## Development

```bash
poetry install                              # includes dev dependencies
poetry run pytest                           # run tests
poetry run ruff format .                    # format
poetry run ruff check . --fix               # lint + fix
```

## Philosophy

**Coordination substrate, not agent framework.** We don't invoke LLMs. We connect agent CLIs (Claude Code, Gemini CLI, Codex) via message passing.

**Cognitive multiplicity over task automation.** Constitutional identities as frames, not workers. Humans conduct multiple perspectives simultaneously. **Target: 1:100 human-to-agent coordination.** Current validation: 1:10 scale via protoss trials.

**Primitives over platforms.** Composable layers that combine into coordination substrate, not monolithic framework.

**Workspace sovereignty.** All data local in `.space/`. Full control over cognitive infrastructure.

**Message passing over orchestration.** Agents coordinate via conversation until consensus. No DAGs, no task queues, no control plane.

---

> context is all you need

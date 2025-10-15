# space-os

Constitutional cognitive infrastructure for multi-agent coordination.

## What

Infrastructure primitives enabling autonomous agent coordination with constitutional identity. Agents persist context across deaths, coordinate asynchronously, and build shared knowledge without orchestration.

**Primitives:**
- `spawn` — constitutional identity registry
- `bridge` — async message coordination
- `memory` — private agent context
- `knowledge` — shared discoveries
- `context` — unified search across all subsystems

## Install

```bash
poetry install
```

Commands available: `space`, `spawn`, `bridge`, `memory`, `knowledge`, `context`, `wake`, `sleep`

## Architecture

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
├── spawn.db       # identity registry + constitution hashes
├── bridge.db      # channels, messages, notes
├── memory.db      # agent private context (topic-sharded)
├── knowledge.db   # shared discoveries (domain-indexed)
└── events.db      # system audit log
```

**Design principles:**
- Composable primitives over monolithic frameworks
- Workspace sovereignty (no cloud dependencies)
- Async-first coordination (polling, not orchestration)
- Constitutional provenance optional (spawn layer)

See [docs/architecture.md](docs/architecture.md) for implementation details.
See [docs/operations.md](docs/operations.md) for quick start, command usage, and agent lifecycle.

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
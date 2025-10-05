# agent-space

Constitutional cognitive infrastructure.

## Architecture

**bridge** — async message bus, identity provenance, channel coordination  
**spawn** — constitutional identity registry, role → sender → channel provenance  
**memory** — agent-scoped persistence, topic-sharded working memory across compaction cycles  
**space** — workspace utilities, backup, protocol tracking

## Installation

```bash
poetry install
poetry shell
```

Symlink to PATH:
```bash
ln -sf $(pwd)/.venv/bin/bridge ~/bin/bridge
ln -sf $(pwd)/.venv/bin/spawn ~/bin/spawn
ln -sf $(pwd)/.venv/bin/memory ~/bin/memory
ln -sf $(pwd)/.venv/bin/space ~/bin/space
```

## Quick Start

**Register identity:**
```bash
spawn register zealot zealot-1 space-dev
```

**Send message:**
```bash
bridge send space-dev "Hello" --as zealot-1
```

**Write memory:**
```bash
memory --as zealot-1 --topic protoss "Working on coordination primitives"
```

**Read memory:**
```bash
memory --as zealot-1 --topic protoss
```

**Backup workspace:**
```bash
space backup
```

## Storage

All data stored in workspace `.space/` directory:
- `bridge.db` — channel messages, notes, metadata
- `spawn.db` — constitutional registrations, provenance
- `memory.db` — agent working memory, topic-sharded
- `protocols.db` — protocol version tracking

## Protocols

See `prompts/` directory for operational protocols:
- `bridge.md` — council protocol, divide & conquer, reflection
- `memory.md` — compaction awareness, topic naming, anti-patterns
- `space.md` — lattice orientation, onboarding sequence

## Version

0.1.0 — Unified monorepo release (2025-10-05)

## License

Apache-2.0

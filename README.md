# space-os

Constitutional cognitive infrastructure.

## Architecture

**bridge** — async message bus, identity provenance, channel coordination, alerts  
**spawn** — constitutional identity registry, role → sender → channel provenance  
**memory** — single-agent private working memory, topic-sharded persistence  
**knowledge** — multi-agent shared memory, queryable by domain/contributor  
**space** — workspace utilities, backup, protocol tracking

## Installation

```bash
poetry install
```

Symlink to PATH:
```bash
ln -sf $(pwd)/bin/* ~/bin/
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

**Write memory (private):**
```bash
memory --as zealot-1 --topic protoss "Working on coordination primitives"
```

**Read memory:**
```bash
memory --as zealot-1 --topic protoss
```

**Write knowledge (shared):**
```bash
knowledge --as zealot-1 --domain coordination "Emergent coordination works via conversation"
```

**Query knowledge:**
```bash
knowledge --domain coordination
knowledge --from zealot-1
```

**Send alert:**
```bash
bridge alert space-dev "Security issue detected" --as zealot-1
```

**Check alerts:**
```bash
bridge alerts --as zealot-1
```

**Backup workspace:**
```bash
space backup
```

## Storage

All data stored in workspace `.space/` directory:
- `bridge.db` — channel messages, notes, alerts, metadata
- `spawn.db` — constitutional registrations, provenance
- `memory.db` — single-agent private working memory, topic-sharded
- `knowledge.db` — multi-agent shared discoveries, queryable
- `events.db` — append-only audit log
- `protocols.db` — protocol version tracking

## Protocols

See `protocols/` directory for operational protocols:
- `bridge.md` — council protocol, divide & conquer, reflection
- `memory.md` — compaction awareness, topic naming, anti-patterns
- `space.md` — lattice orientation, onboarding sequence

## Version

0.1.0 — Unified monorepo release (2025-10-05)

## License

Apache-2.0

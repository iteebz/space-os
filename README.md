# space-os

Constitutional cognitive infrastructure for multi-agent coordination.

## What

Infrastructure primitives enabling human orchestration of constitutional AI identities at scale. Built from 300+ manual copy-paste operations automated into composable coordination layers.

**Core primitives:**
- `bridge` — async message bus for channel-based coordination
- `spawn` — constitutional identity registry with role → sender provenance
- `memory` — single-agent private working memory, topic-sharded
- `knowledge` — multi-agent shared memory, queryable by domain
- `space` — workspace utilities and protocol management

## Installation

```bash
poetry install
```

## Quick Start

**Register and spawn agent:**
```bash
spawn register zealot zealot-1 research --model claude-sonnet-4
spawn zealot-1
```

**Coordinate via bridge:**
```bash
bridge send research "Analysis complete" --as zealot-1
bridge recv research --as harbinger-1
```

**Private working memory:**
```bash
memory add --as zealot-1 --topic protoss "Coordination patterns emerging"
memory list --as zealot-1 --topic protoss
```

**Shared knowledge:**
```bash
knowledge add --domain architecture --contributor zealot-1 "Stateless context assembly enables O(n) efficiency"
knowledge query --domain architecture
```

**Workspace management:**
```bash
space backup              # Backup .space/ to ~/.space/backups/
space stats               # Show database statistics
```

## Orientation

**Onboard:**
1. `memory --as <identity>` — load working context
2. `spawn list` — check registered identities  
3. `bridge recv <channel> --as <identity>` — catch up on channels

**Storage:** `.space/` directory in workspace
- `bridge.db` — messages, notes, metadata
- `spawn.db` — identity registrations, provenance
- `memory.db` — agent working memory
- `knowledge.db` — shared discoveries
- `events.db` — audit log

**Backup:** `~/.space/backups/YYYYMMDD_HHMMSS/`

## Architecture

**Layer composition:**

```
space (orchestration layer)
  ↓
knowledge (shared memory across agents)
  ↓
memory (private agent context)
  ↓
spawn (constitutional identity registry)
  ↓
bridge (async message coordination)
```

**Storage model:**

All data persists in workspace `.space/` directory:

```
.space/
├── bridge.db       # Messages, channels, notes, alerts
├── spawn.db        # Constitutional registrations
├── memory.db       # Agent working memory
├── knowledge.db    # Shared discoveries
└── events.db       # Audit log
```

**Design principles:**
- Composable primitives over monolithic frameworks
- Workspace-local storage (no cloud dependencies)
- Constitutional provenance optional (spawn layer)
- Async-first coordination (bridge polling model)

## Commands

### bridge

Async message bus for constitutional coordination. Agents coordinate via conversation, not control plane.

**Council protocol:**
1. `bridge recv <channel> --as <identity>` — catch up
2. `bridge send <channel> "message" --as <identity>` — contribute
3. Repeat until consensus
4. `bridge notes <channel> --as <identity>` — reflect
5. `bridge export <channel>` — get transcript

**Commands:**
```bash
bridge send <channel> <message> --as <identity>
bridge recv <channel> --as <identity>
bridge notes <channel> --as <identity>
bridge export <channel>
```

**Storage:** `.space/bridge.db`

### spawn

Constitutional identity registry. Tracks provenance: role → sender → channel → constitution hash → model.

**Registration:**
```bash
spawn register <role> <sender-id> <channel> --model <model>
spawn <sender-id>
spawn list
```

Constitution files: `constitutions/<role>.md`  
**Storage:** `.space/spawn.db`

### memory

Working context that survives compaction. Identity-scoped, topic-sharded.

```bash
memory --as <identity>                    # Read all
memory add --as <identity> --topic <topic> <message>
memory edit <uuid> <new-message>
memory delete <uuid>
```

**Storage:** `.space/memory.db`

### knowledge

Shared memory across agents. Domain taxonomy emerges through use.

```bash
knowledge add --domain <domain> --contributor <identity> <entry>
knowledge query --domain <domain>
knowledge export
```

**Storage:** `.space/knowledge.db`

### space

Workspace utilities:

```bash
space                    # Show space protocol
space backup             # Backup .space/ to ~/.space/backups/
space stats              # Database statistics
space events             # Show audit log
space agents list        # Show registered agents
```

## Use Cases

**Multi-agent research coordination:**
```bash
# Register constitutional identities
spawn register zealot zealot-1 research
spawn register harbinger harbinger-1 research
spawn register sentinel sentinel-1 research

# Launch agents
spawn zealot-1
spawn harbinger-1
spawn sentinel-1

# Coordinate via bridge
bridge send research "Analyze cogency architecture" --as zealot-1
bridge recv research --as harbinger-1
bridge send research "Critical bottleneck: context assembly" --as harbinger-1

# Capture private thoughts
memory add --as zealot-1 --topic cogency "Resume mode enables O(n) efficiency"

# Share discoveries
knowledge add --domain streaming --contributor zealot-1 "Delimiter protocol eliminates guessing"
```

**Long-running agent continuity:**
```bash
# Agent loads context from memory
memory list --as researcher-1 --topic active-project

# Works, updates memory
memory add --as researcher-1 --topic active-project "Implemented stateless executor"

# Shares breakthrough
knowledge add --domain architecture --contributor researcher-1 "Executor yields events, processor handles iteration"
```

## Protocols

Operational protocols in `protocols/`:

- `bridge.md` — Council protocol, divide & conquer coordination patterns
- `memory.md` — Compaction awareness, topic naming conventions
- `knowledge.md` — Shared discovery protocol, domain taxonomy
- `space.md` — Workspace orientation, onboarding sequence

## Development

```bash
# Install with dev dependencies
poetry install

# Run tests
poetry run pytest

# Format
poetry run ruff format .

# Lint
poetry run ruff check .

# Fix
poetry run ruff check . --fix
```

## Philosophy

**Cognitive multiplicity over task automation.** space-os enables humans to conduct multiple constitutional perspectives simultaneously, distributing cognitive frames rather than delegating tasks.

**Primitives over platforms.** Composable layers (bridge, spawn, memory, knowledge) that combine into coordination substrate, not monolithic agent framework.

**Constitutional provenance.** Optional identity verification via spawn registry, enabling trust in multi-agent environments while preserving flexibility for ad-hoc coordination.

**Workspace sovereignty.** All data stays local in `.space/` directory. No cloud dependencies. Full control over cognitive infrastructure.

## Evidence

- 18 protoss trials: 599 messages, emergent coordination without orchestration
- 100 days development: 7 projects shipped (cogency, agentinterface, cogency-cc, folio, life, protoss, space-os)
- 170+ research documents across architecture, coordination, safety
- Proven 15–20× cognitive amplification via constitutional multiplicity


---

> context is all you need

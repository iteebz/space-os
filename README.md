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
pip install space-os
```

Or with poetry:

```bash
git clone https://github.com/yourusername/space-os
cd space-os
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

Channel-based async coordination:

```bash
bridge send <channel> <message> --as <identity>     # Send to channel
bridge recv <channel> --as <identity>               # Catch up on messages
bridge wait <channel> --as <identity>               # Poll for new messages
bridge council <channel> --as <identity>            # Interactive TUI
bridge notes <channel> --as <identity>              # Add reflection notes
bridge export <channel>                             # Export full transcript
bridge alert <channel> <message> --as <identity>    # High-priority signal
bridge alerts --as <identity>                       # View alerts
```

### spawn

Constitutional identity registry:

```bash
spawn register <role> <sender-id> <channel> --model <model>  # Register agent
spawn <sender-id>                                            # Launch registered agent
spawn list                                                   # Show registrations
spawn unregister <sender-id> <channel>                       # Remove registration
```

### memory

Single-agent private working memory:

```bash
memory add --as <identity> --topic <topic> <message>    # Write memory
memory list --as <identity> --topic <topic>             # Read topic
memory list --as <identity>                             # Read all topics
memory edit <uuid> <new-message>                        # Edit entry
memory delete <uuid>                                    # Delete entry
memory clear --as <identity> --topic <topic>            # Clear topic
```

### knowledge

Multi-agent shared memory:

```bash
knowledge add --domain <domain> --contributor <identity> <entry>    # Add knowledge
knowledge query --domain <domain>                                   # Query by domain
knowledge query --contributor <identity>                            # Query by contributor
knowledge export                                                    # Export markdown
```

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

See [meta.md](https://github.com/yourusername/space-os/blob/main/docs/meta.md) for complete architecture analysis.

## License

Apache-2.0

---

> context is all you need

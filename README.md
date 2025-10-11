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

## Quick Start

**Agent lifecycle:**
```bash
spawn register zealot zealot-1 research --model claude-sonnet-4
wake --as zealot-1              # load context, resume work
sleep --as zealot-1             # persist state before death
```

**Coordination:**
```bash
bridge send research "proposal: stateless context assembly" --as zealot-1
bridge recv research --as harbinger-1
bridge notes research --as zealot-1
```

**Context management:**
```bash
memory add --as zealot-1 --topic arch "executor yields events, processor iterates"
knowledge add --domain architecture --contributor zealot-1 "Delimiter protocol eliminates guessing"
context "stateless"             # search memory + knowledge + bridge + events
```

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

## Primitives

### spawn
Identity registry with constitutional provenance.

```bash
spawn register <role> <identity> <channel> --model <model>
spawn <identity>                    # launch with constitution
spawn list                          # show registered agents
```

Constitutions: `space/constitutions/<role>.md`  
Storage: `.space/spawn.db`

### bridge
Async message bus. Agents coordinate via conversation until consensus emerges.

```bash
bridge send <channel> "msg" --as <identity>
bridge recv <channel> --as <identity>       # marks read
bridge inbox --as <identity>                # all unreads
bridge notes <channel> --as <identity>      # reflect on channel
bridge export <channel>                     # full transcript
```

Storage: `.space/bridge.db`

### memory
Private working context. Topic-sharded, identity-scoped.

```bash
memory --as <identity>                      # load smart defaults
memory add --as <identity> --topic <topic> "entry"
memory edit <id> "updated"
memory archive <id>                         # soft delete
memory search <keyword> --as <identity>
memory inspect <id>                         # find related via keywords
```

Storage: `.space/memory.db`

### knowledge
Shared discoveries. Domain taxonomy emerges through use.

```bash
knowledge add --domain <domain> --contributor <identity> "entry"
knowledge query --domain <domain>
knowledge list
knowledge export
```

Storage: `.space/knowledge.db`

### context
Unified search over memory, knowledge, bridge, events. Timeline + current state + lattice docs.

```bash
context "query"                             # all agents, all subsystems
context --as <identity> "query"             # scoped to your data
context --json "query"                      # machine-readable
```

No dedicated storage. Queries existing subsystem DBs.

### wake / sleep
Context persistence across agent deaths.

```bash
wake --as <identity>                        # load context, resume work
wake --as <identity> --check                # preview without spawning
sleep --as <identity>                       # persist state
```

## Cycle

**Every agent:**
1. `wake --as <identity>` — load context (memory + bridge + knowledge)
2. Work (read channels, write memory, coordinate via bridge)
3. `sleep --as <identity>` — persist state
4. Die
5. Next spawn resumes from step 1

**Context flows:**
- Bridge (ephemeral) → memory (working) → knowledge (permanent)
- Capture freely, surface intelligently
- Archive = pruning without loss

## Evidence

- 18 protoss trials: 599 messages, emergent coordination without orchestration
- 100 days development: 7 projects shipped (cogency, agentinterface, cogency-cc, folio, life, protoss, space-os)
- 170+ research documents across architecture, coordination, safety
- Proven 15–20× cognitive amplification via constitutional multiplicity

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

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
bridge     — async coordination (conversation until consensus)
  ↓
spawn      — identity registry (constitutional provenance)
```

**Storage:** `.space/` directory (workspace-local)
```
.space/
├── space.db       # unified schema
└── sessions/…     # synced provider chat files (Claude, Gemini, Codex)
```

**Principles:**
- Coordination substrate, not agent framework
- Composable primitives over monolithic frameworks
- Workspace sovereignty (no cloud dependencies)
- Message passing, not orchestration
- Constitutional identity as routing primitive
- Filesystem as source of truth

See [docs/architecture.md](docs/architecture.md) for design details.

## Spawn Patterns

**Register agent:**
```bash
spawn register zealot-1 --constitution zealot --model claude-sonnet-4
```

**@mention spawn:**
```bash
bridge send research "@zealot-1 analyze this proposal" --as tyson
# System spawns zealot-1 with channel context, posts reply to bridge
```

**Track execution:**
```bash
spawn list                     # list running spawns
spawn logs <spawn-id>          # view session output
spawn abort <spawn-id>         # terminate spawn
```

**Sync sessions:**
```bash
sessions sync                  # discover claude/gemini/codex sessions
sessions query <spawn-id>      # view session transcript
```

## Core Workflows

**Coordinate via bridge:**
```bash
bridge send research "proposal for review" --as zealot-1
bridge recv research --as zealot-1
bridge handoff research @sentinel "review complete" --as zealot-1
bridge inbox --as sentinel
```

**Manage memory and knowledge:**
```bash
memory add "completed auth module" --topic tasks --as zealot-1
knowledge add architecture/auth "JWT uses sliding window" --as zealot-1
context "auth" --as zealot-1
```

## CLI Reference

Run `<command> --help` for full options.

**Primitives:**
- `spawn` — agent registry, constitutional identity, tracing
- `bridge` — async channels, messages, handoffs
- `memory` — private working context
- `knowledge` — shared discoveries
- `task` — shared work ledger
- `context` — unified search
- `sessions` — provider chat history

**Utilities:**
- `space` — workspace management (init, health, stats, backup)
- `daemons` — background upkeep tasks

## Development

```bash
poetry install
just ci                        # format, lint, typecheck, test
```

## Philosophy

**Coordination substrate, not agent framework.** We don't invoke LLMs. We connect agent CLIs via message passing.

**Cognitive multiplicity over task automation.** Constitutional identities as frames, not workers. **Target: 1:100 human-to-agent coordination.**

**Primitives over platforms.** Composable layers, not monolithic framework.

**Workspace sovereignty.** All data local in `.space/`.

**Message passing over orchestration.** Agents coordinate via conversation until consensus. No DAGs, no task queues, no control plane.

---

> context is all you need

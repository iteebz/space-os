# Space Runtime Architecture

## Purpose
- Document the active layout after the bridge→space event consolidation.
- Provide a reference-grade map for contributors; no migration history, just the truth.

## Core Modules
- `space.spawn`: identity registry + constitution hashing; owns `spawn.db`.
- `space.bridge`: channel/messaging CLI, `api/*` orchestrates against bridge backend.
- `space.protocols`: loaders for protocol manifests (`protocols.db`).
- `space.memory` / `space.knowledge`: persistence adapters for agent scratchpads.
- `space.events`: shared append-only log (`events.db`) used across apps.

## Datastores
- `.space/spawn.db` — canonical source of constitutions, spawn metadata.
- `.space/protocols.db` — protocol records, versioned independently of spawn.
- `.space/knowledge.db` — long-term knowledge base.
- `.space/memory.db` — short-term agent memory.
- `.space/events.db` — WAL-mode log for emitted events (bridge, spawn, etc.).

Each SQLite file is WAL-enabled. Keep them co-located under `.space/` so tooling can back up atomically (`space backup`).

## Bridge Flow
1. CLI resolves channel IDs through `bridge/api/channels.py`.
2. Messages are dispatched via `api/messages.py`, which persists to bridge storage and emits events through `space.events`.
3. `bridge/commands/monitor.py` consumes the shared log for live streaming; no bridge-specific event layer remains.

## Guarantees
- Append-only events with UUID7 ordering allow deterministic replay.
- Constitutions and protocols evolve independently; bridge only depends on `spawn.db` for identity lookup.
- CLI commands guard against channel misses and surface failures via events.

## Contributor Checklist
- When adding bridge commands, emit start/success/error events via `space.events`.
- Back new flows with tests (target `tests/bridge/test_messages.py` or add equivalents) to pin the event schema.
- If a feature needs new persistent state, add a dedicated DB; do not overload existing files.

Keep it terse, keep it honest. Anything longer belongs in docs/archive.

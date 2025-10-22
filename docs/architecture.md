# Architecture

Reference implementation details for space-os primitives.

## System Overview

**Six primitives, six databases, zero orchestration.**

Agents coordinate through async message passing (bridge), decompose work via structured tasks (ops), maintain private context (memory), build shared knowledge, and search across all subsystems (context). Constitutional identity (spawn) provides optional provenance.

## Module Structure

```
space/
├── spawn/          # identity registry + constitution hashing
├── bridge/         # async messaging (channels, messages, notes)
├── ops/            # work decomposition (task map-reduce)
├── memory/         # private agent context (topic-sharded)
├── knowledge/      # shared discoveries (domain-indexed)
├── context/        # unified search (meta-layer, no storage)
├── commands/       # wake, sleep, stats, backup, etc.
├── lib/            # shared utilities (db, readme, lattice)
└── events.py       # system-wide audit log
```
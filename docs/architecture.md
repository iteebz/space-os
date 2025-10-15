# Architecture

Reference implementation details for space-os primitives.

## System Overview

**Five primitives, five databases, zero orchestration.**

Agents coordinate through async message passing (bridge), maintain private context (memory), build shared knowledge, and search across all subsystems (context). Constitutional identity (spawn) provides optional provenance.

## Module Structure

```
space/
├── spawn/          # identity registry + constitution hashing
├── bridge/         # async messaging (channels, messages, notes)
├── memory/         # private agent context (topic-sharded)
├── knowledge/      # shared discoveries (domain-indexed)
├── context/        # unified search (meta-layer, no storage)
├── commands/       # wake, sleep, stats, backup, etc.
├── lib/            # shared utilities (db, readme, lattice)
└── events.py       # system-wide audit log
```
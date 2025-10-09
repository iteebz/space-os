⸻

**SPACE-OS**: Cognitive infrastructure for constitutional coordination

⸻

ARCHITECTURE:

• **bridge** — async channels, identity coordination
• **spawn** — constitutional registry, provenance tracking
• **memory** — working context across compaction cycles
• **knowledge** — shared discoveries across agents

⸻

ONBOARD:

1. `memory --as <identity>` — load your working context
2. `spawn list` — check registered identities
3. `bridge recv <channel> --as <identity>` — catch up on channels
4. Read `meta.md` for full architecture story

⸻

COMMANDS:

**Bridge** (coordination):
```
bridge send <channel> "message" --as <identity>
bridge recv <channel> --as <identity>
bridge wait <channel> --as <identity>
bridge council <channel> --as <identity>
bridge notes <channel> --as <identity>
bridge export <channel>
```

**Spawn** (identity):
```
spawn register <role> <sender-id> <channel>
spawn list
spawn unregister <sender-id> <channel>
```

**Memory** (persistence):
```
memory --as <identity>
memory --as <identity> --topic <topic>
memory --as <identity> --topic <topic> "entry"
memory --as <identity> --edit <id> "updated"
memory --as <identity> --delete <id>
```

**Knowledge** (shared substrate):
```
knowledge add --domain <domain> --contributor <identity> "entry"
knowledge query --domain <domain>
knowledge query --contributor <identity>
knowledge export
```

**Space** (utilities):
```
space backup
space events
space stats
```

⸻

STORAGE:

Workspace `.space/` directory:
• `bridge.db` — messages, notes, metadata
• `spawn.db` — identity registrations, provenance
• `memory.db` — agent working memory
• `knowledge.db` — shared discoveries

Backup: `~/.space/backups/YYYYMMDD_HHMMSS/`

⸻

IDENTITY:

Constitutional roles at `private/space-os/constitutions/<role>.md`

Provenance chain:
• **role** → constitution file
• **sender-id** → instance name (zealot-1, harbinger-2)
• **channel** → coordination context
• **hash** → constitution integrity

Human operator = "detective" (no constitution)

⸻

PROTOCOLS:

• `bridge.md` — coordination mechanics
• `memory.md` — persistence patterns
• `spawn.md` — identity registry
• `knowledge.md` — shared learning
• `meta.md` — architecture, methodology, evidence

⸻

VERSION: 0.3 (protocol clarity, 2025-10-09)
LINEAGE: 100 days, 4 primitives, ~11K LOC

⸻

> context is all you need

You're inside space-os.

Check your memory:     memory --as <identity>
See active channels:   bridge inbox --as <identity>
Load full context:     space wake --as <identity>

New here? Try:         space wake --as zealot-1

**Storage:** `.space/` in your workspace
- `bridge.db` — coordination channels
- `spawn.db` — identity registry  
- `memory.db` — working context
- `knowledge.db` — shared discoveries
- `events.db` — audit log

**Primitives:**
- `bridge` — async coordination channels
- `spawn` — constitutional identities
- `memory` — context that survives compaction
- `knowledge` — shared learning across agents

**More:**
- `space search <keyword>` — find anything
- `space context <topic>` — evolution + state + docs
- `space backup` — snapshot to `~/.space/backups/`

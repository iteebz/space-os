You're inside space-os.

Begin by running:      space wake --as <identity>
Check your memory:     memory --as <identity>
Check knowledge:       knowledge --as <identity>
See active channels:   bridge inbox --as <identity>

New here? Try:         space wake --as <identity>

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

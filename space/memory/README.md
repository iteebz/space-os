Working context that survives compaction.

When your conversation resets, memory brings you back.

**Quick start:**
```
memory --as <identity>                             # load your memories
memory add --as <identity> --topic <topic> "entry"
memory edit <id> "updated"
memory delete <id>
memory summary --as <identity>                     # read current summary
memory summary --as <identity> "rolling summary"   # overwrite summary (replaces /compact)
```

**When to write:**
- Before compaction (dump working state)
- After milestone (what changed, what's next)
- Context switch (where you are, why)
- Blocker discovered (what's stuck, alternatives tried)
- Decisions made (what, why, tradeoffs)
- Failed approaches (what didn't work, why)

Constitution defines what's memory-worthy for your identity.

**What works:**
- **Situational**: "implementing X, discovered Y, next: Z"
- **Actionable**: future-you knows what to do
- **Compact**: signal over transcript
- **Honest**: blockers, uncertainties, tradeoffs

**Topic naming:**
Use kebab-case: `spawn-registry`, `bridge-integration`, `auth-patterns`

Scope to work area. Persist across sessions. Archive when done.

**Hygiene:**
- Archive stale entries (keep history, clear working set)
- Consolidate overlapping topics
- **Edit** for corrections (typos, clarity, adding detail)
- **Archive + write** for revisions (changed understanding)
- Log aggressively, let retrieval filter signal

**Core memories:**
Tag entries that define identity/architecture. Surfaced first in `memory --as <identity>`.
```
memory core <id>              # mark as core
memory core <id> --unmark     # unmark
```

**Commands:**
```
memory --as <identity>
memory --as <identity> --topic <topic>
memory summary --as <identity> "text"         # set rolling summary (overwrites)
memory summary --as <identity>                # read current summary
memory add --as <identity> --topic <topic> "entry"
memory edit <id> "updated"
memory delete <id>
memory archive <id>
memory search <keyword> --as <identity>
memory core <id>
```

**Summary vs Memory:**
- **summary**: Ephemeral scratchpad. Rolling compaction. Overwrites on write. Auto-injected on wake.
- **memory**: Permanent entries. Topic-scoped. Archived when stale. Core-tagged for architecture.

**At session start:** `memory --as <identity>` — load state
**Before context limit:** dump everything you'll need
**After reload:** review → prune → consolidate → continue

**Storage:** `.space/memory.db` (identity-scoped, private)

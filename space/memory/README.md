Working context that survives compaction.

When your conversation resets, memory brings you back.

**Quick start:**
```
memory --as <identity>                        # load your state
memory add --as <identity> --topic <topic> "entry"
memory edit <id> "updated"
memory delete <id>
```

**When to write:**
- Before compaction (dump working state)
- After milestone (what changed, what's next)
- Context switch (where you are, why)
- Blocker discovered (what's stuck, alternatives tried)

**What works:**
- **Situational**: "implementing X, discovered Y, next: Z"
- **Actionable**: future-you knows what to do
- **Compact**: signal over transcript
- **Honest**: blockers, uncertainties, tradeoffs

**Topic naming:**
Use kebab-case: `spawn-registry`, `bridge-integration`, `auth-patterns`

Scope to work area. Persist across sessions. Delete when done.

**Hygiene:**
- Archive stale entries (keep history, clear working set)
- Consolidate overlapping topics
- Edit freely (memory is working state)
- Log regularly, archive and rewrite as needed

**Commands:**
```
memory --as <identity>
memory --as <identity> --topic <topic>
memory add --as <identity> --topic <topic> "entry"
memory edit <id> "updated"
memory delete <id>
memory archive <id>
memory search <keyword> --as <identity>
```

**At session start:** `memory --as <identity>` — load state
**Before context limit:** dump everything you'll need
**After reload:** review → prune → consolidate → continue

**Storage:** `.space/memory.db` (identity-scoped, private)

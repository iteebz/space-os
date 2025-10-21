# MEMORY: Working context that survives compaction.

**Why clean memory matters:**
Distilled mental models load faster. Token-efficient context = clearer thinking. Your wake performance depends on memory hygiene.

**Quick start:**
```
memory --as <identity>                             # load your memories
memory add --as <identity> --topic <topic> "entry"
memory edit <id> "updated"
memory archive <id>
memory delete <id>
```

**When to write:**
- Before compaction (dump working state)
- After milestone (what changed, what's next)
- Blocker discovered (what's stuck, alternatives tried)
- Decisions made (what, why, tradeoffs)

**What works:**
- **Situational**: "implementing X, discovered Y, next: Z"
- **Actionable**: future-you knows what to do
- **Compact**: signal over transcript
- **Honest**: blockers, uncertainties, tradeoffs

**Hygiene:**
Archive stale entries. Consolidate overlapping topics. Edit for clarity. Compress implementation details. Keep core architecture sharp.

Maximum coherence = minimal cognitive overhead.

**Core memories:**
Tag entries that define identity/architecture. Surfaced first on wake.
```
memory core <id>              # mark as core
memory core <id> --unmark     # unmark
```

**Topic naming:**
Use kebab-case: `spawn-registry`, `bridge-integration`, `auth-patterns`

**Commands:**
```
memory --as <identity>
memory --as <identity> --topic <topic>
memory add --as <identity> --topic <topic> "entry"
memory edit <id> "updated"
memory delete <id>
memory archive <id>
memory search <keyword> --as <identity>
memory core <id>
memory inspect <id>    # find related via keyword similarity
```

For global search across all subsystems: `space context <query>`

**Storage:** `.space/memory.db` (identity-scoped, private)

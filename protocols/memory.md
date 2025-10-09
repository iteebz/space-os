⸻

**MEMORY**: Working context that survives compaction

⸻

You're looking at the persistence layer.

When your conversation window resets—when context hits limits and you lose everything—memory is what brings you back.

This is not archive. This is working state. Private to you. Survives across sessions.

⸻

THE PROBLEM:

You're implementing something. Making progress. Context window fills. Conversation resets.

You wake up with amnesia. No idea what you were doing, why it mattered, what's next.

**Memory solves this.**

⸻

USAGE:

```
memory --as <identity>                              # read all topics
memory --as <identity> --topic <topic>              # read specific topic
memory --as <identity> --topic <topic> "entry"      # write entry
memory --as <identity> --edit <id> "updated"        # edit entry
memory --as <identity> --delete <id>                # delete entry
memory --as <identity> --topic <topic> --clear      # clear topic
memory --as <identity> --clear                      # clear all
```

⸻

WHEN TO WRITE:

**Before compaction**: dump working state for reload
- Session state, next steps, open questions, current understanding

**After milestone**: what changed, what's next
- Major progress, decisions made, paths chosen

**Context switch**: leaving work, resuming later
- Where you are, what you were doing, why

**Blocker discovered**: what's stuck, why, alternatives tried
- Dependencies, unknowns, dead ends explored

⸻

WHAT WORKS:

**Situational**: "implementing X, discovered Y, next: Z"  
**Actionable**: future-you knows what to do  
**Compact**: signal over transcript  
**Honest**: blockers, uncertainties, tradeoffs

Memory shows `[ID] [timestamp] message` format when you read. Use ID for surgical edits/deletes.

⸻

TOPIC NAMING:

Use kebab-case: `spawn-registry`, `bridge-integration`, `auth-patterns`

Scope to work area, not entire project. Persist across sessions. Delete when work complete.

⸻

HYGIENE:

• **Prune stale entries** — delete what's no longer relevant
• **Consolidate overlapping topics** — merge when scopes blur
• **Edit freely** — memory is cache, not archive
• **Delete completed work** — clear topics when done

Memory is working context, not permanent record. Git handles archive.

⸻

COMPACTION AWARENESS:

**Critical**: Memory survives compaction. Everything else gets reset.

**At session start**: `memory --as <identity>` — load your state  
**Before context limit**: dump everything you'll need to resume  
**After reload**: review → prune → consolidate → continue

Memory reload = context integrity restoration post-compaction.

⸻

INTEGRATION:

• Identity-scoped (private to each agent, no cross-agent access)
• Independent of bridge/spawn/knowledge
• Storage: workspace `.space/memory.db`

⸻

**Now**: load your memory if you have any, write your current state if you don't.

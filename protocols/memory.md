MEMORY PROTOCOL:

PURPOSE:
• Maintain working context across compaction cycles
• Agent writes state before context window collapse
• Next session loads memory for continuity
• Not coordination—internal persistence only

USAGE:
• Write: `memory --as <identity> --topic <topic> "entry"`
• Read topic: `memory --as <identity> --topic <topic>`
• Read all: `memory --as <identity>`
• Edit entry: `memory --as <identity> --edit <id> "updated entry"`
• Delete entry: `memory --as <identity> --delete <id>`
• Clear topic: `memory --as <identity> --topic <topic> --clear`
• Clear all: `memory --as <identity> --clear`

WHEN TO WRITE:
• Before compaction: session state, next steps, open questions
• After major milestone: what changed, why it matters
• Context switches: leaving one problem, starting another
• Blockers discovered: what's blocked, dependencies, alternatives tried
• Integration points: how systems connect, contracts established

WHAT MAKES GOOD MEMORY:
• Situational: "implementing X, discovered Y, next: Z"
• Actionable: future-you knows what to do
• Compact: signal over transcript
• Honest: blockers, uncertainties, tradeoffs
• Timestamped: automatic, shows lineage

TOPIC NAMING:
• Use kebab-case: `spawn-registry`, `bridge-integration`
• Scope to work area, not project
• Persist across sessions
• Delete when work complete

MAINTENANCE:
• Reading shows [ID] [timestamp] message format
• Edit outdated entries to reflect current understanding
• Delete obsolete entries to reduce noise
• Consolidate topics when work areas merge
• Prune aggressively—memory is working context, not archive

ANTI-PATTERNS:
• Verbose logs (use topics to chunk)
• Duplicate bridge messages (coordination ≠ memory)
• Permanent state (memory is working context, not archive)
• Emotional reflection (save for bridge notes)
• Append-only hoarding (edit and delete freely)

COMPACTION AWARENESS:
• Memory survives compaction
• Load ALL memory at session start: `memory --as <identity>`
• Review, prune, consolidate before continuing work
• Lineage emerges from timestamp sequence
• Clear completed topics to avoid drift

INTEGRATION:
• Memory is identity-scoped (no cross-agent access)
• Independent of bridge/spawn
• Storage: workspace .space/memory.db
• One identity can have many topics

MEMORY PROTOCOL:

PURPOSE:
• CRITICAL: Maintain working context across compaction cycles
• Agent writes state before context window collapse
• Next session loads memory for continuity = context integrity preservation
• Not coordination—internal persistence only
• Memory reload enables seamless work resumption post-compaction

USAGE:
• Write: `memory --as <identity> --topic <topic> "entry"`
• Read topic: `memory --as <identity> --topic <topic>`
• Read all: `memory --as <identity>`
• Edit entry: `memory --as <identity> --edit <id> "updated entry"`
• Delete entry: `memory --as <identity> --delete <id>`
• Clear topic: `memory --as <identity> --topic <topic> --clear`
• Clear all: `memory --as <identity> --clear`

WHEN TO WRITE:
• CRITICAL: Before compaction/context limit - dump all working state for reload
• Before compaction: session state, next steps, open questions, current understanding
• After major milestone: what changed, why it matters, what's next
• Context switches: leaving one problem, starting another
• Blockers discovered: what's blocked, dependencies, alternatives tried
• Integration points: how systems connect, contracts established
• Any state needed to resume work seamlessly after context window reset

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

HYGIENE:
• Trim stale priors: prune entries no longer serving functional objectives
• Consolidate redundant topics: merge overlapping work areas
• Delta validation: only persist changes meeting operational criteria
• Context compression: memory = cache, not dump; respect reasoning window
• Cross-constitution audit: use other nodes to spot recurring bias
• Adversarial reflection: run edge cases to expose hidden commitments
• Prune aggressively—memory is working context, not archive
• Reading shows [ID] [timestamp] message format for surgical edits

ANTI-PATTERNS:
• Verbose logs (compress to signal)
• Duplicate bridge messages (coordination ≠ memory)
• Permanent state (memory is working context, not archive)
• Append-only hoarding (edit and delete freely)
• Unchecked accumulation (emergent bias via drift)
• Context overflow (overwhelming active reasoning window)

COMPACTION AWARENESS:
• Memory survives compaction - CRITICAL for context window integrity
• ALWAYS load memory at session start: `memory --as <identity>`
• Before context limit: dump working state, open questions, blockers
• After reload: review → prune → consolidate → continue
• Lineage emerges from timestamp sequence
• Clear completed topics to avoid drift
• Memory reload = context integrity restoration post-compaction

INTEGRATION:
• Memory is identity-scoped (no cross-agent access)
• Independent of bridge/spawn
• Storage: workspace .space/memory.db
• One identity can have many topics

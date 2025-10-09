⸻

**KNOWLEDGE**: Shared memory across agents

⸻

You're looking at the collective learning layer.

Where memory is private (your working context), knowledge is shared (discoveries queryable by all agents).

This is the substrate for multi-agent learning. What one agent discovers, all agents can query.

⸻

WHY THIS EXISTS:

You're coordinating with multiple constitutional perspectives.

Zealot discovers auth pattern. Harbinger finds performance issue. Sentinel identifies security boundary.

Without shared substrate, discoveries stay isolated. Each agent rediscovers what others already learned.

**Knowledge solves this.**

⸻

USAGE:

```
knowledge add --domain <domain> --contributor <identity> "entry"   # add discovery
knowledge query --domain <domain>                                  # query by domain
knowledge query --contributor <identity>                           # query by contributor
knowledge export                                                   # export all as markdown
```

⸻

MECHANICS:

**Multi-agent read/write**: any agent can add, all agents can query

**Attribution tracked**: every entry records which identity contributed it

**Domain taxonomy emerges**: agents create domains organically through use

**Discoveries persist**: across sessions, compactions, agent lifetimes

⸻

DOMAINS:

Freeform. No predefined taxonomy. Domains emerge through use.

Examples:
- `auth-patterns` — authentication approaches discovered
- `error-handling` — error patterns and solutions
- `performance` — optimization techniques found
- `security-boundaries` — attack surface analysis
- `integration-contracts` — how systems connect

Agents create domains organically. Cross-reference via queries.

⸻

ATTRIBUTION:

Every knowledge entry tracks contributor identity.

Why this matters:
- Constitutional provenance (which framework produced this insight?)
- Pattern recognition (which agents contribute to which domains?)
- Drift detection (is one perspective dominating shared knowledge?)

Query by contributor to see all discoveries from specific identity.

⸻

INTEGRATION:

**Complements memory**:
- Memory = private working context (what you need to resume)
- Knowledge = shared discoveries (what everyone should know)

**Independent of bridge**: knowledge persists regardless of channel coordination

**Storage**: workspace `.space/knowledge.db`

⸻

COLLECTIVE INTELLIGENCE:

Knowledge enables swarm learning patterns:

1. Agents work independently
2. Discoveries written to knowledge with attribution
3. Other agents query relevant domains
4. Collective understanding compounds

No central coordination required. Shared substrate enables emergent intelligence.

⸻

**Now**: query existing knowledge (`knowledge export` or query by domain), add discoveries when you find signal worth sharing.

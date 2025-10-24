# KNOWLEDGE: Shared discoveries across agents.

Memory is private. Knowledge is shared.

**Quick start:**
```
knowledge list                                          # see all
knowledge about <domain>                                # query domain
knowledge add --domain <domain> --contributor <identity> "entry"
```

**Why it exists:**
One agent discovers something, all agents can query it.

Without shared substrate, every agent rediscovers independently.

**Domains emerge:**
No predefined taxonomy. Agents create domains organically.

Examples: `auth-patterns`, `error-handling`, `performance`, `security-boundaries`

**Commands:**
```
knowledge list
knowledge add --domain <domain> --contributor <identity> "entry"
knowledge about <domain>
knowledge from <identity>
knowledge inspect <uuid>
knowledge archive <uuid>
```

**Attribution:**
Every entry tracks contributor. Constitutional provenance matters.

**Integration:**
- Memory = private working context (what you need)
- Knowledge = shared discoveries (what everyone should know)
- Independent of bridge channels

**Pattern:**
1. Agents work independently
2. Write discoveries to knowledge
3. Others query relevant domains
4. Collective understanding compounds

**Storage:** `.space/knowledge.db` (shared, multi-agent)

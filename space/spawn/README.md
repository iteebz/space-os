Constitutional identity registry.

Tracks who's who: role → instance → channel → constitution hash.

**Quick start:**
```
spawn list                              # see registrations
spawn register <role> <name> <channel>  # bind identity
```

**Example:**
```
spawn register zealot zealot-1 space-dev
spawn register harbinger harb-1 space-dev
spawn list
```

**How it works:**
1. Constitution lives at `constitutions/<role>.md`
2. Registration creates instance (zealot-1, harb-1, etc.)
3. Hash tracks constitution integrity
4. Bridge/memory/knowledge use spawn for identity

**Commands:**
```
spawn list
spawn register <role> <sender-id> <channel>
spawn unregister <sender-id> <channel>
spawn <agent-id>                        # launch with identity
```

**Provenance:**
- **Role** → constitution file (defines behavior)
- **Sender-id** → instance name (zealot-1, harb-alice)
- **Channel** → coordination context
- **Hash** → integrity check

**Storage:** `.space/spawn.db`

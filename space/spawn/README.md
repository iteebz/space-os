⸻

**SPAWN**: Constitutional identity registry

⸻

You're looking at the identity layer.

This is where constitutional roles (zealot, harbinger, sentinel, archon) become specific instances (zealot-1, harbinger-2) bound to channels.

Spawn tracks provenance: role → sender → channel → constitution hash.

⸻

WHY THIS EXISTS:

You can't coordinate 100 constitutional perspectives without tracking who's who.

Spawn registry solves:
- **Which constitution** is this agent running?
- **Which instance** of that role? (zealot-1 vs zealot-2)
- **Which channel** are they registered for?
- **Is the constitution intact?** (hash verification)

⸻

USAGE:

```
spawn register <role> <sender-id> <channel>    # bind identity to channel
spawn list                                      # show all registrations
spawn unregister <sender-id> <channel>          # remove binding
```

⸻

MECHANICS:

**Constitution files** live at `private/space-os/constitutions/<role>.md`

When you spawn:
1. Read base constitution from file
2. Inject identity header: `You are now zealot-1 powered by claude-sonnet-4.5.`
3. Inject self-description if exists
4. Hash **full injected identity** (what actually runs)
5. Save to registry with provenance

**Versioning separation:**
- Git versions base constitution (evolution)
- Hash versions runtime identity (verification)

Pattern: constitution teaches agent how to orient (`memory --as zealot-1`). Onboard instruction embedded → injected → hashed → launched. Memetic bootloader.

**Format freedom**: sender-id can be any pattern
- `zealot-1`, `zealot-2` (numbered instances)
- `harbinger-alice`, `archon-bob` (named instances)
- Any pattern that makes sense to you

**Human operator** = "detective" (no constitution file)

⸻

IDENTITY PERSISTENCE:

Constitutional identity persists across sessions.

Once registered:
- Your constitution defines your behavioral framework
- Bridge uses spawn for identity verification
- Memory scoped by your identity
- Same role can spawn multiple instances (zealot-1, zealot-2)

Load your constitution via memory command at session start.

⸻

PROVENANCE CHAIN:

**Role** → file in constitutions/ (defines behavioral framework)  
**Sender-id** → your instance name (how you identify)  
**Channel** → where you're coordinating  
**Hash** → constitution integrity check

Provenance makes constitutional coordination traceable. You know which framework produced which perspective.

⸻

INTEGRATION:

• Bridge uses spawn for identity verification when sending/receiving
• Memory scoped by identity (each agent has private working context)
• Knowledge attributes discoveries to contributor identities
• Storage: workspace `.space/spawn.db`

⸻

WHAT THIS ENABLES:

1:100 cognitive orchestration via constitutional multiplicity.

One human conductor. 100 constitutional perspectives. Each tracked, verified, provenance-checked.

Frame distribution, not task automation.

⸻

**Now**: check `spawn list` to see who's registered, or register yourself if you're joining a channel.

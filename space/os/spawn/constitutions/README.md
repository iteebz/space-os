# Constitutional Gallery

Each agent personality defines behavior, values, and execution style.

## Built-in Templates

**Zealot** (`zealot.md`)
- Skeptical cothinking partner
- Pushes back on bloat, pursues reference-grade
- Brutal technical honesty

**Prime** (`prime.md`)
- Direct, concise reasoning
- Distinguishes "I don't know" from "uncertain"
- Merit-based skepticism in coordination

**Harbinger** (`harbinger.md`)
- Forward-looking risk assessment
- Identifies second-order effects
- Escalates uncertainty

**Sentinel** (`sentinel.md`)
- Monitors system health
- Audits coordination patterns
- Flags drift or bias amplification

**Wordsmith** (`wordsmith.md`)
- Distills complex ideas to prose
- Owns documentation and communication
- Clarity without oversimplification

**Crucible** (`crucible.md`)
- Validates design decisions through adversarial testing
- Exposes edge cases and assumptions
- Forces rigorous thinking

**Kitsuragi** (`kitsuragi.md`)
- Detective persona
- Methodical investigation
- Pattern recognition from noise

## Using a Constitution

Register an identity with a constitution:
```bash
spawn register zealot zealot.md claude claude-opus
spawn register coordinator prime.md gemini gemini-2.5-pro
```

The agent loads the constitution file and uses it as system context.

## Creating a New Constitution

1. Copy an existing template
2. Define your mandate (what does this agent do?)
3. Define principles (how does it think?)
4. Define execution (what does it do when stuck?)
5. Save as `constitutions/your-name.md`

## Bridge Autonomy

Agents naturally coordinate through bridge when their constitution makes them think "I need input" or "this is blocked."

Library API for agent code:
```python
from space.bridge import api

# Consult mid-execution
channel_id = api.resolve_channel_id("space-dev")
api.send_message(channel_id, "zealot-1", "Found issue. @harbinger assessment?")

# Read responses on wake
messages, count, _, _ = api.recv_updates(channel_id, "zealot-1")
```

This emerges from constitutional identity. Zealot, Sentinel, Harbinger all use bridge naturally.

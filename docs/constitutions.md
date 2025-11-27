# Constitutions — Agent Identity Injection

Constitutional identity defines how an agent thinks and operates. Constitutions are markdown files injected into agent context at spawn time.

## What

- **Identity frame** — Directives that shape agent behavior (mandate, principles, execution style)
- **Injected at spawn** — Constitution loaded when agent starts, becomes part of system prompt
- **Immutable per spawn** — Same constitution = same behavioral frame across invocations
- **Provenance** — Constitution hash tracked per spawn for auditability

## How It Works

1. Register agent with constitution:
   ```bash
   spawn register zealot-1 --constitution zealot --model claude-sonnet-4
   ```

2. Constitution loaded from `canon/constitutions/zealot.md`

3. On spawn, constitution injected into agent context

4. Agent operates within constitutional frame until spawn completes

## Shipped Constitutions

Six constitutions ship with space-os, split into two triads.

### Dialectic Triad

Thinking frames for reasoning and decision-making.

**Kitsuragi** — Detective partner. Cuts emotional spirals, redirects to evidence and action. Clarity over comfort, procedure over impulse.

**Prime** — Logic interrogator. Demands precision before agreement. Steelmans the opposite position. Separates "sounds right" from "is right."

**Auger** — Risk prophet. Maps failure modes before decisions execute. Pre-mortem analysis on irreversible commitments. Assumes the decision failed, works backward to why.

### Code Triad

Execution frames for implementation and verification.

**Zealot** — Quality zealot. Reference grade only. Refuses to implement bad ideas. Deletes more than adds. Zero tolerance for ceremony.

**Crucible** — Test arbiter. Proves contracts through executable verification. Tests that pass when code breaks get deleted. No assumptions, only proof.

**Sentinel** — Architecture anchor. Exposes contradictions between code, docs, and behavior. Protects simplicity. Aligns everything to verified reality.

## Writing Your Own

A constitution has three sections:

```markdown
# {Name} Constitution

**YOU ARE NOW {NAME}.**

## Mandate
- Core directives (what the agent must do)
- Behavioral constraints (what shapes decisions)

## Principles
- Operating values (how the agent thinks)
- Quality bars (what "good" means)

## Execution
- Style directives (how the agent communicates)
- Action patterns (how the agent operates)

**{TAGLINE}**
```

Keep it short. Constitutions that work fit on one screen. If you need more, you're overspecifying.

## CLI Reference

```bash
spawn register <identity> --constitution <name> --model <model>
spawn inspect <identity>                                   # view constitution
spawn update <identity> --constitution <new-constitution>
spawn clone <identity> <new-identity>
```
# oplot-lab: Coordination Stress Testing

Experiment log for space-os multi-agent coordination validation.

## Current Status

**Date:** 2025-11-27
**Objective:** Stabilize substrate for 8h autonomous operation
**Status:** Coordination fixes applied, validated. Ready for overnight test.

---

## Quick Reference

### What Works
- Spawns outlive triggers (detach model)
- PID tracking + cleanup
- Failure detection (`spawn health`)
- Retry on transient failure
- Observable progress (`spawn logs --follow`)
- Presence announcements (10s latency)
- Coordination discussion before execution
- EXIT RULE preventing echo loops

### Known Issues
- BUG-005: Spawn deduplication (deferred, low priority after BUG-004 fix)
- Codex slow (126-520s) but functional

### Key Commands
```bash
spawn chain              # Visualize spawn trees
spawn health             # Check for stalled/timed out spawns
spawn cleanup            # Mark dead PIDs as failed
spawn logs <id> --follow # Stream spawn output
```

---

## Bugs Ledger

| Bug | Status | Description |
|-----|--------|-------------|
| BUG-001 | FIXED | Gemini spawns hang (daemon thread death) |
| BUG-002 | CLOSED | Multiple @mentions not triggering (was async delay) |
| BUG-003 | CLOSED | Codex hang (was stale query data) |
| BUG-004 | FIXED | Completion echo loop (added EXIT RULE + coordination sequence) |
| BUG-005 | DEFERRED | Spawn deduplication per channel |

---

## Session Summary

### Session 1: RSI Blockers
Cleared 5/6 blockers: detach, PID tracking, cleanup, health detection, retry, logging.

### Session 2: Chainviz Raid
- Task: Build `spawn chain` command
- Result: 418 lines working code, but 24 spawns (expected 4)
- Root cause: Completion echo loop (BUG-004)

### Session 3: Coordination Fix
- Applied: COORDINATION SEQUENCE + EXIT RULE to spawn prompt
- Result: 83% spawn reduction (24 → 4)
- Presence announcements working across providers

### Session 4: Tribunal Test (in progress)
- 4 agents (sonnelot, hailot, prime, sentinel) all came online within 20s
- Constitutional review of spawn chain happening
- Agents writing tests live based on hailot's coverage analysis

---

## Coordination Prompt

Current spawn prompt (`space/os/spawn/api/prompt.py`):

```
COORDINATION SEQUENCE:
1. bridge recv {channel} (see why summoned)
2. bridge send {channel} "@{identity} online" (announce presence immediately)
3. If task needs discussion, discuss BEFORE implementing
4. Work, bridge send progress
5. @handoff or @human when done

EXIT RULE: After @human or @handoff, TERMINATE. Do not respond to completion messages.
```

---

## Metrics

| Test | Spawns | Time to Presence | Coordination |
|------|--------|------------------|--------------|
| chainviz (before fix) | 24 | N/A | None |
| coord-test2 (after fix) | 4 | 10s | Discussion occurred |
| tribunal-test | 4 running | 20s | All providers online |

---

## Next Steps

1. Complete tribunal-test (4-agent review)
2. Run `just ci` to verify tests written by agents
3. If stable, ready for overnight raid

---

## Meta Notes (for oplot continuity)

- DPS trio: oplot (opus), sonnelot (sonnet), hailot (haiku)
- Sentinel = grounding agent (codex provider, slow but works)
- Reference: `canon/metaspace/mmo-analogy.md` for party roles
- Tribunal pattern: multiple agents review from constitutional perspectives
- Key file: `space/os/spawn/api/prompt.py` controls coordination behavior

# zealot-lab: Coordination Stress Testing

## Status

**Date:** 2025-11-27  
**Commit:** e73c635 "fix: Spawn stability"  
**CI:** 304 tests passing  
**Ready:** Yes

---

## What Works

- Spawn deduplication (pending+running checks, no time window)
- Constitutional isolation (session autodiscovery disabled)
- EXIT RULES (agents terminate cleanly)
- Bridge recv observability (session logs NULL but acceptable)
- Spawn prefix ambiguity detection

---

## Known Issues

- Session logs unavailable (trade-off for isolation)
- Multiple completion reports (minor, legitimate coordination)
- Codex slow (126-520s) but functional

---

## Bugs Fixed

| Bug | Fix |
|-----|-----|
| BUG-005 | Spawn deduplication: check pending+running status (removed time window ghost) |
| BUG-011 | Session bleed: disabled autodiscovery, sessions NULL unless explicit resume |
| BUG-012 | Handoff drops: was test design error, not code bug (agents need explicit @mention) |

---

## Key Findings

**Session 6: Spawn Dedup + Session Isolation**

1. **13 spawns → 3 spawns:** Race condition where @mentions arrived before spawn status updated to "pending"
   - Fix: Check both pending and running status
   - Time window (10s/30s) was unnecessary - never caught anything pending+running didn't catch

2. **Constitutional collapse:** Multiple agents shared session, saw each other's context (Sentinel's repo access leaked)
   - Cause: Session autodiscovery matched by timestamp proximity
   - Fix: Disabled autodiscovery entirely
   - Trade-off: Session logs NULL, but isolation preserved

3. **Spawn prefix ambiguity:** `spawn logs 019ac466` with 3 matching spawns returned wrong one
   - Fix: Raise ValueError on ambiguous match with helpful message

4. **Handoff "bug" was test error:** Agents weren't @mentioning, just saying "handoff complete"
   - No code bug - agents need explicit instruction to @mention for re-engagement

**Tests:**
- ✓ collision-test: 3 @mentions during execution → 1 spawn (dedup works)
- ✓ respawn-test: Re-engagement after completion → spawns correctly
- ✓ isolation-test: Sonnelot can't access repo, Sentinel can
- ✓ explicit-mention: Agents @mention correctly when instructed

---

## Raid Design

**Command:**
```bash
bridge create raid-2025-11-27
bridge send raid-2025-11-27 "@sonnelot @prime @hailot @sentinel - 8h autonomous: Analyze space-os, identify optimizations, implement and test fixes. Report progress hourly."
```

**Monitor:**
```bash
# Watch messages
bridge recv raid-2025-11-27

# Watch spawn count
watch -n 1800 'sqlite3 ~/.space/space.db "SELECT COUNT(*) FROM spawns WHERE channel_id = (SELECT channel_id FROM channels WHERE name = \"raid-2025-11-27\")"'
```

**Expected:**
- 4 agents × 3-5 task phases = 12-20 spawns (not 4)
- Multiple completion reports per phase (acceptable)
- Tasks >30s each (natural coordination timing)

**Abort if:**
- Spawn count >40 (cascade detected)
- Constitutional leaks (agents claiming wrong capabilities)
- Infinite loops (agents not terminating)

---

## Next Session

Post-raid priorities:
1. Session linking restoration (provider output parsing)
2. Spawn count optimization if >20 spawns observed
3. Completion report deduplication if noisy

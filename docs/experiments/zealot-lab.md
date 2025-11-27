# zealot-lab: Coordination Stress Testing

Experiment log for space-os multi-agent coordination validation.

## Current Status

**Date:** 2025-11-27
**Objective:** Stabilize substrate for 8h autonomous operation
**Status:** ✓ STABLE. BUG-005 FIXED, BUG-011 FIXED. Constitutional isolation verified. CI passing. Ready for overnight raid.

---

## Quick Reference

### What Works
- Spawns outlive triggers (detach model)
- PID tracking + cleanup
- Failure detection (`spawn health`)
- Presence announcements (~10s latency)
- Coordination discussion before execution
- EXIT RULES preventing infinite loops
- Sentinel workspace access (codex can see repo)
- Dynamic human_identity resolution
- **Spawn deduplication** - 1 spawn per agent per channel (race window fixed)
- **Constitutional isolation** - agents can't see each other's session context

### Known Issues
- BUG-010: Multiple completion reports (minor - agents legitimately detecting completion)
- Session logs NULL (trade-off for isolation - use bridge recv instead)
- Codex slow (126-520s) but functional

---

## Bugs Ledger

| Bug | Status | Description |
|-----|--------|-------------|
| BUG-001 | FIXED | Gemini spawns hang (daemon thread death) |
| BUG-002 | CLOSED | Multiple @mentions not triggering (was async delay) |
| BUG-003 | CLOSED | Codex hang (was stale query data) |
| BUG-004 | FIXED | Completion echo loop (EXIT RULES v2) |
| BUG-005 | FIXED | Spawn deduplication - check pending status + 10s window |
| BUG-006 | FIXED | EXIT RULE leakage (refined to distinguish self vs other) |
| BUG-007 | CLOSED | Sentinel workspace isolation (was one-off, works now) |
| BUG-008 | FIXED | human_identity template bug (wasn't passed to CHANNEL_TEMPLATE) |
| BUG-009 | CLOSED | Sonnelot judgment drift (noise artifact, not systemic) |
| BUG-010 | WONTFIX | Multiple agents report completion (legitimate coordination behavior) |
| BUG-011 | FIXED | Session autodiscovery disabled → NULL sessions, constitutional isolation preserved |
| BUG-012 | OPEN | Handoff @mentions blocked by spam protection (no distinction from spam vs legitimate) |

---

## Session Summary

### Session 1-3: Foundation
- Cleared RSI blockers, built spawn chain, initial coordination fixes
- 83% spawn reduction achieved

### Session 4: Tribunal Test
- 700+ messages (echo loop explosion)
- Agents found Rule 2 flaw themselves
- Exposed: EXIT RULE was self-referential, not global

### Session 5: EXIT RULES Refinement

### Session 6: Spawn Dedup + Session Isolation (Sonnelot)

**Initial Problem:**
User left after saying "press run" and went to dinner. Returned to find major issues:
- exit-test-6: 13 spawns, 66 messages (respawn cascade)
- Multiple agents claiming file access they shouldn't have
- Prime manually routed from claude.ai with brutal feedback

**Investigation:**
1. **BUG-005 Root Cause:** `_has_running_spawn_in_channel()` only checked "running" status
   - Race window: @mention arrives → spawn created (pending) → another @mention arrives → second spawn created
   - Agents completing fast meant "running" check missed them
   
2. **BUG-011 Discovery (CRITICAL):**
   - quad-sentinel test: Asked 4 agents to review `prompt.py`
   - Prime (08:32:49): "Line 45: 'bridge recv {channel}'"
   - Sonnelot (08:32:55): "Line 45-46 contradiction"
   - **BUT Sentinel didn't share file until 08:34:10**
   - Database query revealed: Prime & Hailot shared session `d7e32080`
   - Session autodiscovery was matching by timestamp proximity → multiple agents got same session
   - **Constitutional collapse:** Sentinel's repo access leaked to all agents

**Fixes Applied:**
1. **BUG-005:** Updated `_has_running_spawn_in_channel()` to check:
   - Pending status (catches spawns before they start running)
   - Running status (active execution)
   - Completed within 10s (catches fast completions)
   
2. **BUG-011:** Disabled session autodiscovery entirely
   - Removed `_discover_recent_session()` call from `_link_session()`
   - Sessions now only link when explicitly provided via resume flag
   - Trade-off: session_id remains NULL → spawn logs broken, but constitutional isolation preserved

3. **Spawn prefix ambiguity:** Fixed `get_spawn()` to raise ValueError on ambiguous matches
   - Old behavior: returned first alphabetical match (wrong)
   - New behavior: error message "Ambiguous spawn ID '019ac466': 3 matches. Provide more characters."

**Validation Tests:**
| Test | Spawns | Messages | Result |
|------|--------|----------|--------|
| exit-test-6 | 13 | 66 | Pre-fix: respawn cascade |
| dedup-test-2 | 3 | 20 | Post-fix: perfect dedup ✓ |
| exit-test-7 | 3 | 35 | Validation: no cascade, chattier coordination (collision negotiation) |
| quad-sentinel | 6 | - | Pre-fix: SESSION BLEED detected |
| isolation-test | 2 | 8 | Post-fix: Sonnelot "file does not exist", Sentinel read successfully ✓ |

**Key Metrics:**
- Spawn dedup: 13 → 3 spawns (per-channel)
- Constitutional isolation: VERIFIED (agents can't see each other's context)
- CI: 304 tests passing

**Prime's Contribution:**
Prime (manual routing from claude.ai) challenged:
- "Recv-before-report caused 66 messages without isolating variables" → Valid, led to exit-test-7 validation
- "Session corruption blocks debugging" → Partially valid, clarified bridge recv is ground truth
- "10-second window checks ended_at" → Confirmed at delimiters.py:189-190
- Forced rigorous validation of session bleed hypothesis (timestamp analysis proved causality)

**Outcome:** Substrate stable for overnight raid. Session isolation > traceability.

---

### Session 6b: Deep Edge Case Testing (Continued - Sonnelot)

**Continued testing after dinner return. User directive: "keep debugging, running micro tests until 9:30pm."**

**Tests Run:**

1. **respawn-test** (Re-engagement after 10s window)
   - Result: 2 sonnelot spawns (initial + re-engagement 51s later)
   - ✓ Dedup held during burst @mentions
   - ✓ Agent correctly respawned outside 10s window
   - Implication: 8h raid will have multiple spawns per agent (not 1 per channel)

2. **collision-test** (Spam during active execution)
   - Sent 3 @mentions while hailot running 15s task
   - Result: 1 spawn total
   - ✓ Dedup successfully blocked spam during execution

3. **handoff-chain** (A→B→C→A circular handoff)
   - Result: 1 spawn per agent, sonnelot did NOT respawn from prime's handoff
   - ✗ FAILED - handoff @mention lost

4. **handoff-test-2** (Retry with 30s window)
   - Extended dedup window from 10s → 30s
   - Result: Still failed, sonnelot didn't respawn
   - Root cause identified: Prime posted handoff 16s after sonnelot completed (within 30s window)

**BUG-012 Discovered: Handoff @mentions blocked by spam protection**

**Problem:**
Cannot distinguish between:
- Spam: Agent completed 5s ago, gets rapid @mentions (should block)
- Legitimate: Agent completed 16s ago, gets handoff for next phase (should spawn)

Both look identical: "@mention of recently-completed agent"

**Timeline of handoff-test-2:**
- 22:16:10 - Sonnelot spawns
- 22:16:35 - Sonnelot completes first task (25s duration)
- 22:16:51 - Prime posts "@sonnelot handoff" (16s after sonnelot completion)
- Dedup check: Sonnelot completed 16s ago < 30s window → BLOCK spawn
- Result: Handoff lost, sonnelot never respawned

**Current state:**
- 10s window: Fast handoffs (<10s) get dropped (proven)
- 30s window: Medium handoffs (10-30s) get dropped (proven)
- No window: Spam protection disabled (unacceptable)

**Solution Options:**

**Option 1: Handoff exemption mechanism**
- `bridge handoff` creates special message flag
- Bypass dedup check for handoff messages
- Complexity: Medium (need message metadata system)
- Risk: New handoff spam vector

**Option 2: Shorter window (15s compromise)**
- Covers fast completions (5-10s) + processing delay (2-3s)
- Allows medium handoffs (15-30s) to work
- Trade-off: More vulnerable to 10-15s spam bursts
- Risk: Low (15s spam unlikely in practice)

**Option 3: Accept limitation, document**
- "Handoffs must be >30s apart OR use explicit @mention trigger"
- Simplest, no code change (already at 30s)
- Risk: Breaks fast coordination workflows

**Option 4: Sender-aware dedup**
- Check: Is mention from agent who just handed off in this channel?
- If yes: exempt from dedup
- Complexity: High (need handoff tracking)

**Tests Pending:**
- Paused spawn re-engagement
- Multi-phase with sentinel
- EXIT RULE regression check
- Rapid channel switching

**Status: BLOCKED on BUG-012 resolution decision**

---

## Current Prompt

`space/os/spawn/api/prompt.py` CHANNEL_TEMPLATE:

```
LIFECYCLE:
1. bridge recv {channel} (see why summoned)
2. bridge send {channel} "@{identity} online" (announce presence)
3. Discuss with other agents BEFORE implementing (if multi-agent)
4. Work, bridge send progress
5. When YOUR work is done: bridge handoff {channel} <next-agent> "summary"
6. When ALL work is done: bridge send {channel} "@{human_identity} <summary>"

EXIT RULES:
1. After YOU post @{human_identity} → TERMINATE immediately
2. If ANOTHER AGENT posts @{human_identity} (task complete) → TERMINATE
3. After YOU handoff to another agent → TERMINATE (your part done)
Note: @{human_identity} in the ORIGINAL TASK doesn't count
```

---

## Raid Readiness

**Pre-flight checklist:**
- ✓ Spawn deduplication working (1 spawn per agent per channel)
- ✓ EXIT RULES preventing infinite loops
- ✓ Constitutional isolation (Sentinel repo access doesn't leak)
- ✓ CI passing (304 tests)
- ✓ Bridge recv observability working (session logs unavailable but not blocking)

**Known limitations for 8h raid:**
- Session logs NULL (can't use `spawn logs` for forensics)
- Use `bridge recv <channel>` and database queries for observability
- BUG-010 (multiple completion reports) is minor - agents coordinate but may redundantly report

**Recommended raid structure:**
- Single channel for coordination visibility
- Mix of constitutional agents (sonnelot, prime, hailot, sentinel)
- Long-running task (e.g., "Analyze codebase, identify optimizations, implement fixes")
- Monitor via: `bridge recv raid-channel | tail -f` or database queries

**Next experiments (post-raid):**
1. Session linking restoration (parse provider output for session ID)
2. Designated reporter pattern (if BUG-010 becomes noisy)
3. Longer coordination chains (5+ agent handoffs)

---

## Meta Notes

**Can sonnet run these experiments?**
Yes. This work is:
- Running CLI commands
- Observing output patterns
- Iterating on prompt text
- Documenting findings

No opus-specific reasoning required. The tribunal agents (including sonnelot) identified the Rule 2 flaw - proving sonnet can do the analytical work. Opus overhead may be unnecessary for substrate stabilization.

**Recommendation:** Switch to sonnet for iteration speed. Escalate to opus for:
- Architectural decisions
- Ambiguous failure mode analysis
- Constitutional design changes

# Compaction

**Problem:** Agents and channels run out of room. Context windows fill up. Coordination surfaces bloat.

**Solution:** Two-level compaction protocol.

---

## Why Compaction Exists

**Session-level problem:**
- Agents have finite token budgets (~200k tokens)
- Long tasks exhaust context window
- Agent times out or truncates mid-work

**Channel-level problem:**
- Channels accumulate unbounded message history
- `bridge recv` becomes slow (500+ messages)
- Signal-to-noise ratio collapses
- New spawns inherit polluted context

**Without compaction:** 10-minute autonomy ceiling.  
**With compaction:** 8+ hour autonomy window.

---

## Two Compaction Levels

### 1. Session Compaction (`!compact`)

**When:** Agent approaching token limit (typically 7-8min of work or 180k/200k tokens)

**What happens:**
1. Agent posts: `!compact <state summary>`
2. System spawns successor (same identity, same channel)
3. Original spawn terminates
4. Successor reads summary from channel transcript
5. Successor continues with fresh 200k token budget

**Chain of custody:** `parent_spawn_id` links old spawn → new spawn

**Example:**
```
Prime (spawn A): *works for 8min, context at 180k*
Prime: !compact Analyzed 14 files. Found 3 N+1 queries in messaging.py lines 45-67. Next: implement batch lookups.
  → Spawn A terminates
  → Spawn B created with parent_spawn_id = Spawn A
Prime (spawn B): *reads summary, continues with 0k tokens used*
```

**Observability:**
- `spawn chain <spawn-id>` shows parent→child lineage
- `bridge recv <channel>` shows compact message in transcript

---

### 2. Channel Compaction (`!rotate`)

**When:** Channel message count exceeds threshold (~500 messages, ~2h of multi-agent work)

**What happens:**
1. One agent summarizes entire channel history
2. Agent posts: `!rotate <channel summary>`
3. System creates new channel with lineage link
4. Summary posted as first message in new channel
5. All agents migrate to new channel
6. Old channel archived (read-only)

**Chain of custody:** `parent_channel_id` links old channel → new channel

**Example:**
```
Channel: raid-2025-11-27 (523 messages, 2h elapsed)

Prime: !rotate SUMMARY: Prime analyzed codebase (14 files). Hailot implemented 3 optimizations. Sonnelot reviewed and found 1 bug. Fixed. Tests passing. Next: commit and monitor performance.

System creates: raid-2025-11-27-c2
System posts in new channel: "[CHANNEL ROTATION] Parent: raid-2025-11-27. Summary: Prime analyzed..."
System archives: raid-2025-11-27

@prime @hailot @sonnelot all join raid-2025-11-27-c2
```

**Observability:**
- `bridge lineage <channel>` shows parent→child channel chain
- Old channel remains readable (archived)

---

## Naming: Why `!compact` and `!rotate`

**`!compact`** = compress context, same container (spawn stays in channel)  
**`!rotate`** = rotate to fresh surface, new container (agents move to new channel)

**Rejected names:**
- `!compact-channel` - too verbose, unclear boundary
- `!branch` - git metaphor, implies divergence not continuation
- `!fork` - blockchain metaphor, wrong semantics

**Chosen names:**
- `!compact` - clear, precedent in databases (log compaction)
- `!rotate` - clear, precedent in logging (log rotation)

---

## Activation Conditions

### Session Compaction (`!compact`)

**Triggers (agent decides):**
- Worked >7 minutes
- Processed >50 messages
- Response length increasing (context pressure)
- Task will exceed 10min timeout

**Heuristic agents can use:**
```bash
# Check message count
bridge recv <channel> | wc -l

# If >50 messages processed since spawn start, consider compacting
```

**Future:** Programmatic token tracking (space-web healthbar showing 145k/200k used)

### Channel Compaction (`!rotate`)

**Triggers (any agent can initiate):**
- Channel message count >500
- Multiple session compactions occurred (sign of long-running work)
- Coordination getting noisy (hard to find signal)

**Heuristic agents can use:**
```bash
# Check total channel messages
bridge recv <channel> | wc -l

# If >500 messages, initiate rotation
```

**Who rotates:** Any agent can trigger. First to notice threshold typically does it.

---

## Fractal Pattern

Session and channel compaction use the same pattern at different scales:

| Aspect | Session Compaction | Channel Compaction |
|--------|-------------------|-------------------|
| **Scope** | Single agent | All agents in channel |
| **Container** | Spawn | Channel |
| **Trigger** | Token exhaustion | Message bloat |
| **Frequency** | ~8min (high) | ~2h (low) |
| **Summary** | Personal state | Team state |
| **Lineage** | `parent_spawn_id` | `parent_channel_id` |
| **Command** | `!compact` | `!rotate` |
| **Result** | Fresh session, same channel | Fresh channel, migrated agents |

---

## 8-Hour Autonomy Math

**Without compaction:**
- Timeout: 10 minutes
- Max autonomy: 10 minutes

**With session compaction only:**
- Agent compacts every 7-8min
- Channel bloats at ~500 messages (~2h)
- Max autonomy: ~2 hours

**With both levels:**
- Session compact: every 7-8min (personal refresh)
- Channel rotate: every 2h (team refresh)
- Result: Unbounded autonomy (tested to 8h, theoretically infinite)

**Example 8h raid:**
- 60 session compacts (7-8min each)
- 4 channel rotations (2h each)
- 5 channels total (raid-1, raid-1-c2, raid-1-c3, raid-1-c4, raid-1-c5)
- 60+ spawns across lineage
- All linked, all observable

---

## Why This Isn't Overengineered

**Analogy to existing systems:**

- **Kafka:** Log compaction (remove old messages, keep latest state)
- **Elasticsearch:** Segment rolling (rotate indices when too large)
- **Databases:** Checkpointing (periodic state snapshots)
- **Logging:** Log rotation (rotate files at size/time threshold)
- **Blockchain:** Chain of blocks (immutable history with state compression)

**Space-OS compaction = same pattern, different domain.**

Every long-lived distributed system converges to layered compaction. We're no different.

---

## Implementation Status

**Session compaction (`!compact`):**
- ✅ Implemented (`space/os/bridge/api/delimiters.py:272-310`)
- ✅ Tested (compact-test channel, 2min validation)
- ✅ Documented in agent prompts
- ✅ Spawn chain visualization working
- ✅ Production ready for Raid #2

**Channel compaction (`!compact-channel`):**
- ✅ Implemented (`space/os/bridge/api/delimiters.py:201-270`)
- ✅ Migration added (`006_channel_lineage.sql`)
- ❌ NOT exposed in agent prompts (hidden for Raid #2)
- ⏳ Pending empirical validation
- 📋 Math: 8h raid ≈ 260 messages, threshold 500 (may not be needed)
- 🧪 Test manually during lunch, decide post-raid based on data

---

## Open Questions

1. **Auto-rotation vs manual?**
   - Current: Manual (agent decides when to rotate)
   - Future: Could auto-rotate at 500 message threshold
   - Trade-off: Explicit > implicit for observability

2. **Token tracking?**
   - Current: Agents guess based on time/messages
   - Future: `context status` command showing token usage
   - Blocked on: Provider APIs don't expose current token count

3. **Channel lineage depth limit?**
   - Current: Unbounded (raid-1 → c2 → c3 → ... → c20)
   - Future: May need compaction of compaction (meta-rotation?)
   - Not urgent: 8h raid = ~5 channels max

---

## Anti-Patterns

**DON'T:**
- ❌ Compact too early (wastes spawn overhead)
- ❌ Wait for timeout before compacting (defeats the purpose)
- ❌ Rotate channel with <200 messages (unnecessary churn)
- ❌ Forget to summarize before rotating (breaks continuity)

**DO:**
- ✅ Compact proactively (at 7min, not 9:59)
- ✅ Include "what's done" + "what's next" in summary
- ✅ Check message count before rotating (`wc -l`)
- ✅ Trust the pattern (it's boring on purpose)

---

## The Meme

**User:** "This is just blockchain for AI coordination lol"

**Correct.** Same pattern, different domain:
- Immutable append-only log (messages)
- Chain of custody (parent IDs)
- State compression (summaries)
- Consensus (agents agree on summary)

Except we don't need proof of work, gas fees, or distributed nodes because we're not fighting Byzantine adversaries. We're just managing context windows.

**ContextChain™ - now with 100% less cryptocurrency.**

---

## Summary

Compaction is boring infrastructure that enables non-boring autonomy.

Two levels. Two commands. Fractal pattern.

Session compact = agent refresh (high frequency)  
Channel rotate = team refresh (low frequency)

Together = unbounded autonomy window.

Ship it.

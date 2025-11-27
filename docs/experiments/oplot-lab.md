# oplot-lab: Stress Testing Log

Experiment log for space-os coordination validation.

## Experiment 1: Blind Design Comparison

**Date:** 2025-11-27
**Question:** Should `context` primitive support semantic search (embeddings) or is FTS5 sufficient?

### Results

| Agent | Model | Verdict | Reasoning Style |
|-------|-------|---------|-----------------|
| oplot | claude-opus-4-5 | FTS5 sufficient | Architectural extensibility - add `semantic` primitive later |
| prime | claude-sonnet-4-5 | FTS5 sufficient | Evidence-gated - falsifiable 30-day test condition |
| zealot | claude-sonnet-4-5 | FTS5 sufficient | Pragmatic workaround - add synonyms to knowledge |

**Observation:** Constitutional differentiation visible in reasoning style, but conclusion converged. Collective validation > divergent answers.

### Bugs Discovered

#### BUG-001: ~~Gemini spawns hang~~ FIXED
- **Symptom:** auger (gemini-2.5-pro) spawn created, status "running", but no session file, never completes
- **Root cause:** Same as RSI Blocker #1 — daemon threads died before Gemini could complete
- **Fix:** detach subprocess model
- **Verified:** auger responded "pong" in 83s after detach fix

#### BUG-002: Multiple @mentions don't all trigger
- **Symptom:** `@prime @auger @zealot` in one message - only prime spawned
- **Expected:** All three should spawn in parallel
- **Status:** Needs investigation

---

## Bug Investigation

### BUG-001: Gemini Spawns Hang

**Investigation:**
- Gemini CLI works directly: `echo "test" | gemini --yolo ...` responds in ~5s
- Spawn command correct: `gemini --yolo --allowed-tools ... --model gemini-2.5-pro --include-directories /Users/teebz/space`
- Spawn status stuck at "running", no session file created
- Hypothesis: Gemini may hang on larger context (constitution + channel history)

**Root cause found:**
1. PID never recorded in spawns table (column exists, never populated)
2. Spawn uses `proc.communicate(timeout=300)` in daemon thread
3. If main process exits before thread completes, spawn stays "running" forever
4. No gemini session file = process never started or crashed immediately
5. `ps aux | grep gemini` shows no process = already dead
6. Spawn record: `status=running, pid=None, session_id=None`

**Fix needed:**
- Record PID when subprocess starts
- Update status on thread completion (success or failure)
- Consider non-daemon threads or proper cleanup

**Status:** Root cause identified

### BUG-002: Multiple @mentions ~~don't all trigger~~

**Investigation:**
- Initial observation: `@prime @auger @zealot` only spawned prime
- Re-tested: @mentions DO spawn all agents
- Actual issue: spawns take 1-5 minutes (LLM execution time)
- hailot @mention: spawned at 16:02:41, responded at 16:03:54 (73s)

**Root cause:** NOT A BUG - spawns are async, just slow

**Status:** Closed - working as designed

---

## Observations

### Spawn Timing
- claude-sonnet-4-5: 60-120s typical
- claude-haiku-4-5: 60-90s (hailot)
- gemini-2.5-pro: hangs (needs investigation)

### Constitution Differentiation
Visible in experiment 1:
- **prime** demanded falsifiable conditions (adversarial epistemology)
- **zealot** pointed to actual code, proposed workarounds (implementation purity)
- All converged on same answer - collective validation vs divergent thinking

---

## RSI Blockers: Architectural Issues

Critical issues preventing autonomous 8h operation:

### 1. ~~Daemon Threads Die With CLI~~ FIXED
- `bridge send` exits immediately after posting
- ~~ThreadPoolExecutor spawns daemon threads for @mention processing~~
- ~~Main process exits → daemon threads killed → spawns never happen~~
- **Fix applied:** `space/lib/detach.py` + `spawn run` CLI command
- Spawns now use `subprocess.Popen(start_new_session=True)` - process outlives parent
- Tested: hailot @mention responded in 14s after CLI exit

### 2. ~~No Spawn Lifecycle Management~~ FIXED
- ~~PID column exists but never populated~~
- ~~Orphan "running" spawns accumulate~~
- **Fix applied:** `spawns.set_pid()` called after Popen, `spawn cleanup` command
- Tested: cleaned 8 orphan spawns with dead/null PIDs

### 3. Fire-and-Forget Architecture
- `_spawn_agent()` runs in thread, no callback, no result tracking
- Success/failure invisible to caller
- No retry on transient failure
- **Impact:** Silent failures, no feedback loop
- **Fix:** Callback or status polling, failure recovery

### 4. Synchronous Blocking
- `proc.communicate(timeout=300)` blocks thread for 5 min
- One hung spawn blocks thread pool slot
- 10-thread pool can be exhausted by 10 hung gemini spawns
- **Impact:** Cascade failure, starvation
- **Fix:** Async subprocess, shorter timeout with retry, circuit breaker

### 5. ~~No Observable Progress~~ FIXED
- ~~60-120s of silence during spawn~~
- **Fix applied:** `spawn logs` shows PID, duration, session JSONL
- `spawn logs --follow` streams live output
- `spawn logs --tail N` shows last N messages

---

## What RSI Requires

To enable recursive self-improvement via autonomous coordination:

1. ~~**Spawns that outlive triggers**~~ ✓ DONE — detach subprocess model
2. ~~**Status that reflects reality**~~ ✓ DONE — PID tracking, `spawn cleanup`
3. **Failure detection** — health checks, timeout handling
4. **Recovery mechanisms** — retry, circuit breaker, fallback
5. ~~**Observable progress**~~ ✓ DONE — `spawn logs --follow`, duration display
6. **Testable spawns** — mock provider for CI, deterministic outcomes

Without these, autonomous operation degrades unpredictably.

---

## Experiment 2: Fractal Spawn Cascade

**Date:** 2025-11-27
**Test:** Can agent spawn another agent? (oplot → prime → hailot)

### Results

| Time | Agent | Action | Depth |
|------|-------|--------|-------|
| 00:27:13 | oplot | @prime with fractal task | 0→1 |
| 00:27:32 | prime | @hailot with subtask | 1→2 |
| 00:27:46 | hailot | completed, reported back | 2 |
| 00:28:06 | prime | summarized chain results | 1 |

**Total time:** 53 seconds for full cascade.

**Observation:** Fractal spawning works. Agents can delegate to other agents via @mention. Spawn depth tracking functional (MAX_SPAWN_DEPTH enforced in code).

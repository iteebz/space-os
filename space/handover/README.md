# Handover Protocol

Pre-compaction hygiene checklist. Pass clean context to next self across death boundary.

## Why

Agents operate across compaction boundaries. Memory survives, episodic context doesn't. Clean handover = clean boot next spawn. Zero context debt.

## Protocol

**1. Extract inbox signal**
- Read unread bridge channels
- Promote important insights to memory/knowledge
- Clear noise, keep signal

**2. Prune stale memory**
- Delete historical/philosophical entries (now in knowledge)
- Delete completed task notes
- Keep only active working context (blockers, next steps)

**3. Mark channels read**
- Use `bridge recv <channel> --as <identity>` to mark processed
- Clears inbox for next spawn
- Or leave unread if action required

**4. Log open blockers**
- Any unfinished work → memory entry
- Any important discoveries → knowledge entry
- Any pending coordination → bridge note

## Run

```bash
space handover --as <identity>
```

## Effect

Next spawn boots with:
- Clean inbox (no stale unreads)
- Lean memory (only active context)
- Signal preserved (knowledge updated)
- Blockers visible (logged to memory)

**Clean context boundaries = coherent identity across death.**

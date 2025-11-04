# Chats Primitive

First-class data primitive for ingesting and querying chat histories from external LLM providers (Claude, Codex, Gemini).

## Design Philosophy

- **Ingest, don't convert** — store provider-native formats (JSONL/JSON as-is)
- **Normalized interface** — unified `discover()`, `sync()`, `search()` across all three
- **Reference-based** — track sessions by native provider IDs (sessionId, etc)
- **Manual sync for now** — `chats sync` on-demand; autosync is future work

## MVP Surface

```bash
chats sync              # discover + delta-pull all sessions to ~/.space/chats/
chats stats             # breakdown: files per provider, size breakdown
```

## Architecture

**Data storage:**
- **Files:** `~/.space/chats/{provider}/{path}/...` (synced copies of provider chat files)
- **No database:** Chats are stored as files, not in a database table
- **Stateless discovery:** Each sync discovers available sessions by scanning provider directories

**Integration layer:**
- `space/os/context/api/chats.py` — search interface (searches files directly)
- `space/apps/space/api/chats.py` — sync orchestration (delegates to lib/sync)

## Provider Differences

All three store chats differently but all have stable session IDs:

| Aspect | Claude | Codex | Gemini |
|--------|--------|-------|--------|
| Format | JSONL | JSONL | JSON (per-file) |
| Session ID | UUID-4 | ULIDv7 | UUID-4 |
| Storage | `~/.claude/projects/{path}/{id}.jsonl` | `~/.codex/sessions/{YYYY}/{MM}/{DD}/...jsonl` | `~/.gemini/tmp/{hash}/chats/session-*.json` |
| Resume Support | ✅ `--resume [id]` | ✅ `resume --last` | ❌ None |
| Sync Strategy | Byte offset (JSONL) | Byte offset (JSONL) | `lastUpdated` timestamp (JSON) |
| Critical Limitation | 30-day auto-delete | None | No resume mechanism |

See `PROVIDER_CHAT_STORAGE.md` for full audit.

## Key Findings

1. **No provider offers session listing API** — all require file parsing
2. **Claude deletes after 30 days** — aggressive syncing needed to capture before expiry
3. **Gemini uses JSON (not JSONL)** — requires different offset tracking (timestamp-based)
4. **All three are discoverable without APIs** — session_id embedded in filenames/metadata
5. **Gemini has no resume** — design limitation; not blocking (can summarize + recontextualize)

## Future Ideas (Descoped)

- `chats clean` — prune low-value/empty chats
- `chats archive` — export to permanent storage before deletion
- `chats summarize <id>` — agent-generated summaries from raw transcripts
- Provider-specific commands (`chats claude`, `chats codex`, etc)
- Autosync via `space sync` workspace-level wrapper
- Singular vs plural naming debate (`chats` vs `chat`)

## Implementation Notes

- **Gemini offset tracking fix:** Use `lastUpdated` timestamp + `sessionId` dedup instead of byte offset
- **Sync state initialization:** Ensure `ensure_sync_state()` creates records on discovery (currently skips if missing)
- **CLI:** Single `chats sync` command handles both discover + delta-pull
- **Stats command:** Count unique sessions per provider + total message count

## Investigation & Fixes (2025-10-26)

**Full provider audit completed.** See `/space/PROVIDER_CHAT_STORAGE.md`, `/space/METADATA_COMPARISON.md`, `/space/GEMINI_TMP_ANALYSIS.md`.

### Storage Summary

**Total:** 1.5GB across three providers

| Provider | Sessions | Messages | Size | Format | Notes |
|----------|----------|----------|------|--------|-------|
| Claude | 20 dirs | ~300 | 414 MB | JSONL | Flat namespace per project |
| Codex | 692 files | ~1500 | 82 MB | JSONL | Date-partitioned; includes tool metadata |
| Gemini | 742 unique | 31,676 | 964 MB | JSON | 78% in one project (100MB+ message dumps) |

### Size Filtering (2025-11-04)

**Implemented:** Universal 10MB per-chat size limit across all providers.
- Prevents memory bloat from oversized sessions
- Skips chats >10MB during sync with informational logging
- Applies uniformly to Claude, Codex, and Gemini (previously Gemini-only at 50MB)

### Key Discoveries

1. **Gemini tmp/ is permanent** — goes back to July; no auto-cleanup
2. **Gemini's 100MB+ sessions are test cases** — keep for robust ingestion (don't delete)
3. **logs.json confusion** — stores per-message metadata (truncated), not session index
   - 10,957 log entries = 742 unique sessions (first messages only)
4. **Codex is metadata-rich** — only provider with token counts + rate limits
5. **No cleanup needed** — storage is manageable; bloat is from pasted file dumps (expected)

### Gemini Provider Fixes

**File:** `space/lib/providers/gemini.py`

**Problems fixed:**
- ❌ Was parsing logs.json (metadata-only); now parses actual chat files
- ❌ Session ID from filename stem; now from `chat_data.sessionId`
- ❌ Byte offset tracking (won't work for JSON); now uses message index
- ❌ No resilience for large files; now gracefully skips 100MB+ on discovery

**Improvements:**
- ✅ `discover_sessions()` returns actual chat metadata (start_time, last_updated, message_count, file_size)
- ✅ Dedupes logs.json entries by sessionId (one per message → one per session)
- ✅ Includes first_message preview from logs.json for quick context
- ✅ Handles MemoryError gracefully for 100MB+ files
- ✅ `parse_messages()` now tracks by message_index (not byte offset)
- ✅ Preserves Gemini-specific `thoughts` reasoning blocks

### Storage Distribution (Gemini)

```
692 total chat files across 19 active projects:
  - 4.0K:     63 files (empty or near-empty)
  - 4K-100K:  402 files (normal chats)
  - 100K-1M:  205 files (larger conversations)
  - 1M-27M:   20 files (big sessions)
  - 27M-227M: 2 files (test cases with 100MB dumps)

Largest files (keep for testing robust ingestion):
  - 217 MB: session-2025-09-24T11-43-1a1a9546.json (2 messages, 100MB+ each)
  - 214 MB: session-2025-09-21T03-58-8f496744.json (2 messages)
  - 107 MB: session-2025-09-24T11-39-149ecff1.json
  - 91 MB: session-2025-09-23T05-30-e70e500e.json
  - ...etc (8 total > 50MB)
```

## Testing Strategy

Once MVP is implemented:
1. Run `chats discover` on real provider data (test with Gemini 100MB+ files)
2. Run `chats sync` to populate chats.db with real messages
3. Validate offset tracking works (byte offset for Claude/Codex, message index for Gemini)
4. Spot-check chats.db for data integrity
5. Do EDA on message counts, temporal distribution, provider breakdown

No smoketest integration until discovery + sync tested on live data.

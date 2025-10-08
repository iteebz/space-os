Bridge Architecture Reference
=============================

Scope
-----
Working summary of the `space.bridge` architecture across active branches (`main`, `proto`, `harbinger`, `gemilot`). Focus is on defects in `main`, fixes present on the other branches, and trade-offs that block immediate migration.

`main`
------
- Layout: legacy split (`api/` orchestrates, `storage/` persists) with direct imports (`space/bridge/api/*.py`, `space/bridge/storage/*.py`).
- Known defects (uncovered during review, no tests yet):
  - Bookmark flow: `api/messages.py` passes `agent_id` where `storage.get_new_messages` expects `last_seen_id`, causing duplicate delivery and broken unread counts. Needs proto’s guard before writing bookmarks.
  - Backup CLI: `bridge.cli.backup` imports `bridge.backup.backup_bridge_data`; module never existed on `main`, so the command crashes at runtime.
- Strength: compatible with current CLI tooling, minimal coupling to spawn. Weakness: bug-prone cross-layer calls, no tests for the hot paths above.

`proto`
-------
- Architecture: same layout as `main`. Keeps CLI compatibility.
- Fix coverage:
  - Bookmark handling is corrected; `recv_updates` derives unread counts locally and writes bookmarks only after retrieving new rows.
  - Storage uses `get_db_connection` (no stray imports from `space.lib.db`).
- Limitations: still lacks spawn/context integration introduced later; no contextual app structure. Requires cherry-pick of fixes into `main` to eliminate regressions without a wholesale migration.

`harbinger`
-----------
- Architecture shift: introduces `space/apps/*` context packages with adapters that wrap bridge/storage/cli concerns. Bridge becomes one app alongside spawn/memory.
- Benefits: modular “context” layout, better separation between api logic and IO, unified CLI entry points per app.
- Trade-offs: assumes spawn-first identity + channel provenance; bridge CLI now routes through context adapters, meaning any consumer expecting the old module paths breaks. Migration would pull spawn-specific semantics into bridge even for non-constitutional agents.

`gemilot`
---------
- Evolution of `harbinger`: doubles down on the apps/context model and introduces council-focused orchestration (bridge CLIs tuned for council operations).
- Benefits: clean council transcript tooling, higher-level protocols baked into app interfaces.
- Trade-offs: narrows compatibility—general-purpose bridge CLI flows from `main`/`proto` are gone. Integration expects council agents only; legacy CLI parity is lost.

Recommendation
--------------
- Stay on `main` layout, but port the `proto` fixes (bookmark handling, backup wiring) under test-first workflow.
- Add regression tests before patching:
  1. Bookmark persistence + unread counts for `api.messages.recv_updates` / `storage.messages.get_new_messages`.
  2. `bridge.cli.backup` command resolving the correct helper module.
- Revisit `harbinger`/`gemilot` once tests exist and the team is ready to absorb the spawn/council coupling.
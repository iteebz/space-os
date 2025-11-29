"""Session linker: find and link spawn_id to session_id."""

import json
import logging
import time
from pathlib import Path

from space.lib import paths, store

logger = logging.getLogger(__name__)


def find_session_for_spawn(
    spawn_id: str, provider: str, created_at: str, cwd: str | None = None
) -> str | None:
    """Find session_id via marker-based matching.

    Strategy:
    1. Search provider's native session dir (Claude: ~/.claude/projects/{cwd}/)
    2. Fall back to our archive (~/.space/sessions/)

    Args:
        spawn_id: Spawn UUID to find session for
        provider: Provider name (claude, codex, gemini)
        created_at: Spawn creation timestamp for mtime fallback
        cwd: Working directory to scope search (Claude only)
    """
    from space.lib.uuid7 import short_id

    marker = short_id(spawn_id)
    created_ts = _parse_iso_timestamp(created_at)

    search_dirs: list[Path] = []

    if provider == "claude" and cwd:
        from space.lib.providers.claude import Claude

        native_dir = Claude.SESSIONS_DIR / Claude.escape_cwd(cwd)
        if native_dir.exists():
            search_dirs.append(native_dir)

    archive_dir = paths.sessions_dir() / provider
    if archive_dir.exists():
        search_dirs.append(archive_dir)

    if not search_dirs:
        return None

    closest_file = None
    closest_distance = float("inf")

    for search_dir in search_dirs:
        for session_file in search_dir.glob("*.jsonl"):
            found_marker = _parse_spawn_marker(session_file)
            if found_marker == marker:
                session_id = _extract_session_id(session_file)
                if session_id:
                    logger.info(f"Matched spawn {spawn_id[:8]} to session {session_id} via marker")
                    return session_id

            file_mtime = session_file.stat().st_mtime
            distance = abs(file_mtime - created_ts)
            if distance < closest_distance:
                closest_distance = distance
                closest_file = session_file

    if closest_file:
        session_id = _extract_session_id(closest_file)
        if session_id:
            logger.warning(
                f"Matched spawn {spawn_id[:8]} to session {session_id} via mtime (marker not found)"
            )
            return session_id

    return None


def link_spawn_to_session(spawn_id: str, session_id: str | None) -> None:
    if not session_id:
        logger.debug(f"Spawn {spawn_id} has no session_id, skipping link")
        return

    try:
        # Import here to avoid circular dependency
        from . import sync

        # Sync this specific session from provider (e.g., ~/.claude/projects/)
        # This creates/updates the session record in the DB
        sync.ingest(session_id=session_id)

        # Now link spawn to session (FK constraint satisfied)
        with store.ensure() as conn:
            conn.execute(
                "UPDATE spawns SET session_id = ? WHERE id = ?",
                (session_id, spawn_id),
            )
            conn.commit()
        logger.info(f"Linked spawn {spawn_id} to session {session_id}")
    except Exception as e:
        logger.warning(
            f"Failed to link spawn {spawn_id} to session {session_id}: {e}. "
            "Spawn created but session_id not linked. Will retry during provider sync."
        )


def _truncate_spawn_id(spawn_id: str) -> str:
    """DEPRECATED: Use uuid7.short_id() instead (uses last 8 chars for entropy)."""
    return spawn_id[:8]


def _extract_session_id(session_file: Path) -> str | None:
    """Extract session ID from JSONL file (first line or filename)."""
    try:
        first_line = session_file.read_text().split("\n")[0]
        if first_line:
            data = json.loads(first_line)
            session_id = data.get("sessionId") or data.get("id")
            if session_id:
                return session_id
        return session_file.stem
    except (json.JSONDecodeError, OSError, IndexError):
        return session_file.stem


def _parse_spawn_marker(session_file: Path) -> str | None:
    """Extract spawn_marker from session JSONL (all provider formats).

    Early exit: Marker always appears in first user message.

    Handles:
    - Claude: {"message": {"content": "spawn_marker: abc12345..."}}
    - Codex: {"role": "user", "content": "spawn_marker: abc12345..."}
    - Gemini: {"role": "user", "content": "spawn_marker: abc12345...", "timestamp": "..."}
    """
    try:
        with open(session_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)

                    # Check if this is a user message
                    is_user = (
                        data.get("type") == "user"
                        or data.get("role") == "user"
                        or (
                            "message" in data
                            and isinstance(data["message"], dict)
                            and data["message"].get("role") == "user"
                        )
                    )

                    marker = _extract_marker_from_line(data)
                    if marker:
                        return marker

                    # Early exit after first user message (marker would be there)
                    if is_user:
                        return None

                except json.JSONDecodeError:
                    continue
        return None
    except OSError:
        return None


def _extract_marker_from_line(data: dict) -> str | None:
    """Extract 8-char spawn_marker from single JSONL line (provider-agnostic)."""
    # Claude format: {"message": {"content": "..."}}
    if "message" in data:
        msg = data["message"]
        if isinstance(msg, dict):
            content = msg.get("content", "")
            if isinstance(content, str):
                marker = _parse_marker_from_text(content)
                if marker:
                    return marker

    # Codex/Gemini format: {"content": "..."} or {"role": "user", "content": "..."}
    content = data.get("content", "")
    if isinstance(content, str):
        return _parse_marker_from_text(content)

    return None


def _parse_marker_from_text(text: str) -> str | None:
    """Extract 8-char marker from text containing 'spawn_marker: <marker>'."""
    if "spawn_marker:" not in text:
        return None

    marker_part = text.split("spawn_marker:")[-1].strip()
    marker = marker_part.split()[0] if marker_part else ""

    return marker if len(marker) == 8 else None


def _parse_iso_timestamp(iso_str: str) -> float:
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(iso_str)
        return dt.timestamp()
    except (ValueError, AttributeError):
        return time.time()


__all__ = [
    "find_session_for_spawn",
    "link_spawn_to_session",
]

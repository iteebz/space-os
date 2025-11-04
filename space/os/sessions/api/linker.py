"""Session linker: find and link spawn_id to session_id."""

import json
import logging
import time
from pathlib import Path

from space.lib import paths, store

logger = logging.getLogger(__name__)


def find_session_for_spawn(spawn_id: str, provider: str, created_at: str) -> str | None:
    """Find session_id for a spawn via marker or closest mtime.

    Algorithm:
    1. Scan provider session directory for files
    2. Check if any file contains spawn_id[:8] marker (preferred)
    3. If no marker found, sort by |file.mtime - spawn.created_at| and use closest
    4. Extract session_id from matching file

    Args:
        spawn_id: Full spawn UUID7 (e.g., "abc12345-def6-...")
        provider: Provider name (claude, gemini, codex)
        created_at: ISO timestamp of spawn creation

    Returns:
        session_id if found, None otherwise
    """
    marker = _truncate_spawn_id(spawn_id)
    session_dir = paths.sessions_dir()
    provider_dir = session_dir / provider

    if not provider_dir.exists():
        logger.warning(f"Provider session dir not found: {provider_dir}")
        return None

    session_files = list(provider_dir.glob("*.jsonl"))
    if not session_files:
        return None

    for session_file in session_files:
        if _parse_spawn_marker(session_file) == marker:
            return _extract_session_id(session_file)

    sorted_files = _scan_provider_sessions(provider, created_at)
    if sorted_files:
        session_id = _extract_session_id(sorted_files[0])
        if session_id:
            return session_id

    return None


def link_spawn_to_session(spawn_id: str, session_id: str | None) -> None:
    """Link spawn to session by syncing provider data.

    Ensures FK constraint is satisfied by triggering sync_session
    before updating the spawn record. This approach elegantly handles the timing
    issue: session doesn't exist in DB until provider sync runs.

    Notes:
    - Calls sync_session(session_id) to create session record
    - Session record synced from provider files (e.g., ~/.claude/projects/)
    - Links are idempotent: safe to call multiple times
    - If sync fails, gracefully continues (session may sync later)

    Args:
        spawn_id: Full spawn UUID7
        session_id: Provider-native session UUID (or None if not found)
    """
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
    """Get first 8 characters of spawn_id (UUID7 truncated for marker)."""
    return spawn_id[:8]


def _scan_provider_sessions(provider: str, created_at: str) -> list[Path]:
    """Scan provider session dir, return files sorted by mtime distance.

    Args:
        provider: Provider name (claude, gemini, codex)
        created_at: ISO timestamp string to calculate mtime distance

    Returns:
        List of session files sorted by closest mtime distance
    """
    created_ts = _parse_iso_timestamp(created_at)
    session_dir = paths.sessions_dir()
    provider_dir = session_dir / provider

    if not provider_dir.exists():
        return []

    files_with_distance = []
    for session_file in provider_dir.glob("*.jsonl"):
        file_mtime = session_file.stat().st_mtime
        distance = abs(file_mtime - created_ts)
        files_with_distance.append((distance, session_file))

    files_with_distance.sort(key=lambda x: x[0])
    return [f[1] for f in files_with_distance]


def _extract_session_id(session_file: Path) -> str | None:
    """Extract session_id from JSONL file header.

    First line should have session metadata. Look for 'id' field.

    Args:
        session_file: Path to JSONL session file

    Returns:
        session_id if found in header, None otherwise
    """
    try:
        first_line = session_file.read_text().split("\n")[0]
        if not first_line:
            return None
        data = json.loads(first_line)
        return data.get("id")
    except (json.JSONDecodeError, OSError, IndexError):
        return None


def _parse_spawn_marker(session_file: Path) -> str | None:
    """Extract spawn_id[:8] marker from JSONL content.

    Looks for 'spawn_marker: XXXXXXXX' pattern in any message content.

    Args:
        session_file: Path to JSONL session file

    Returns:
        spawn_id[:8] marker if found, None otherwise
    """
    try:
        content = session_file.read_text()
        for line in content.split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                msg_content = data.get("content", "")
                if isinstance(msg_content, str) and "spawn_marker:" in msg_content:
                    marker_part = msg_content.split("spawn_marker:")[-1].strip()
                    marker = marker_part.split()[0]
                    if len(marker) == 8:
                        return marker
            except json.JSONDecodeError:
                continue
        return None
    except OSError:
        return None


def _parse_iso_timestamp(iso_str: str) -> float:
    """Convert ISO timestamp string to Unix timestamp.

    Args:
        iso_str: ISO format timestamp (e.g., "2025-01-01T12:00:00")

    Returns:
        Unix timestamp as float
    """
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

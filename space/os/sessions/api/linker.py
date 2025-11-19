"""Session linker: find and link spawn_id to session_id."""

import json
import logging
import time
from pathlib import Path

from space.lib import paths, store

logger = logging.getLogger(__name__)


def find_session_for_spawn(spawn_id: str, provider: str, created_at: str) -> str | None:
    """Find session_id via marker or closest mtime match."""
    marker = _truncate_spawn_id(spawn_id)
    session_dir = paths.sessions_dir()
    provider_dir = session_dir / provider

    if not provider_dir.exists():
        logger.warning(f"Provider session dir not found: {provider_dir}")
        return None

    created_ts = _parse_iso_timestamp(created_at)
    closest_file = None
    closest_distance = float("inf")

    for session_file in provider_dir.glob("*.jsonl"):
        if _parse_spawn_marker(session_file) == marker:
            return _extract_session_id(session_file)

        file_mtime = session_file.stat().st_mtime
        distance = abs(file_mtime - created_ts)
        if distance < closest_distance:
            closest_distance = distance
            closest_file = session_file

    if closest_file:
        session_id = _extract_session_id(closest_file)
        if session_id:
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
    return spawn_id[:8]


def _extract_session_id(session_file: Path) -> str | None:
    try:
        first_line = session_file.read_text().split("\n")[0]
        if not first_line:
            return None
        data = json.loads(first_line)
        return data.get("id")
    except (json.JSONDecodeError, OSError, IndexError):
        return None


def _parse_spawn_marker(session_file: Path) -> str | None:
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

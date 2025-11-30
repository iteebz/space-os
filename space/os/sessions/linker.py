"""Session linker: find and link spawn_id to session_id."""

import logging
from pathlib import Path

from space.lib import paths, store
from space.lib.providers import Claude, Codex, Gemini

logger = logging.getLogger(__name__)

PROVIDERS = {"claude": Claude, "codex": Codex, "gemini": Gemini}


def find_session_for_spawn(
    spawn_id: str, provider: str, created_at: str, cwd: str | None = None
) -> str | None:
    """Find session_id via marker-based matching.

    Searches provider's native dirs and archive for spawn_marker match.
    """
    from space.lib.uuid7 import short_id

    provider_cls = PROVIDERS.get(provider)
    if not provider_cls:
        return None

    marker = short_id(spawn_id)

    for search_dir in provider_cls.native_session_dirs(cwd):
        if not search_dir.exists():
            continue
        session_id = _search_dir_for_marker(search_dir, marker, provider_cls, spawn_id)
        if session_id:
            return session_id

    archive_dir = paths.sessions_dir() / provider
    if archive_dir.exists():
        session_id = _search_dir_for_marker(
            archive_dir, marker, provider_cls, spawn_id, pattern="*.jsonl"
        )
        if session_id:
            return session_id

    return None


def _search_dir_for_marker(
    search_dir: Path,
    marker: str,
    provider_cls,
    spawn_id: str,
    pattern: str | None = None,
) -> str | None:
    """Search directory for session with matching marker.

    Searches newest files first (most likely to contain the marker).
    """
    file_pattern = pattern or getattr(provider_cls, "SESSION_FILE_PATTERN", "*.jsonl")

    for session_file in search_dir.rglob(file_pattern):
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    for session_file in files:
        found_marker = provider_cls.parse_spawn_marker(session_file)
        if found_marker == marker:
            session_id = provider_cls.session_id_from_contents(session_file) or session_file.stem
            logger.info(f"Matched spawn {spawn_id[:8]} to session {session_id} via marker")
            return session_id

    return None


def link_spawn_to_session(spawn_id: str, session_id: str | None) -> None:
    """Link spawn to session in database."""
    if not session_id:
        logger.debug(f"Spawn {spawn_id} has no session_id, skipping link")
        return

    try:
        from . import sync

        sync.ingest(session_id=session_id)

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


__all__ = [
    "find_session_for_spawn",
    "link_spawn_to_session",
]

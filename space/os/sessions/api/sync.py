"""Session sync: discover, ingest, and index provider sessions."""

import json
import logging
from dataclasses import dataclass

from space.lib import paths, providers, store

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    """Progress event with provider and counts."""

    provider: str
    discovered: int
    synced: int
    total_discovered: int = 0
    total_synced: int = 0
    phase: str = "sync"
    indexed: int = 0
    total_indexed: int = 0


def _index_transcripts(session_id: str, provider: str, content: str, conn) -> int:
    """Index session JSONL content into transcripts table for FTS5 search.

    Parses user and assistant messages from JSONL and populates the transcripts table.
    Tool calls and results are skipped (noise reduction for search).

    Args:
        session_id: Session UUID
        provider: Provider name (claude, codex, gemini)
        content: JSONL content (one JSON object per line)
        conn: Database connection (caller handles transaction)

    Returns:
        Number of messages indexed
    """
    from datetime import datetime

    indexed_count = 0
    rows = []

    for msg_idx, line in enumerate(content.strip().split("\n")):
        if not line.strip():
            continue

        try:
            msg_data = json.loads(line)
        except json.JSONDecodeError:
            continue

        role = msg_data.get("role", "").lower()
        if role not in ("user", "assistant"):
            continue

        msg_content = msg_data.get("content", "")
        if isinstance(msg_content, list):
            msg_content = "\n".join(
                [
                    block.get("text", "")
                    if isinstance(block, dict) and block.get("type") == "text"
                    else ""
                    for block in msg_content
                ]
            ).strip()

        msg_content = str(msg_content).strip()
        if not msg_content:
            continue

        timestamp_str = msg_data.get("timestamp")
        timestamp_int = 0

        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                timestamp_int = int(dt.timestamp())
            except (ValueError, AttributeError):
                timestamp_int = 0

        rows.append((session_id, msg_idx, provider, role, msg_content, timestamp_int))
        indexed_count += 1

    if rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO transcripts
            (session_id, message_index, provider, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    return indexed_count


def discover() -> list[dict]:
    """Discover all sessions from all providers.

    Returns:
        List of {cli, session_id, file_path, created_at, ...}
    """
    all_sessions = []
    provider_map = {"claude": "Claude", "codex": "Codex", "gemini": "Gemini"}

    for cli_name, class_name in provider_map.items():
        try:
            provider_class = getattr(providers, class_name)
            provider = provider_class()
            sessions = provider.discover()
            all_sessions.extend(sessions)
        except Exception as e:
            logger.warning(f"Error discovering {cli_name} sessions: {e}")

    return all_sessions


def ingest(session_id: str) -> bool:
    """Ingest one session: copy/convert to ~/.space/sessions/{provider}/.

    Args:
        session_id: Session ID to ingest

    Returns:
        True if successfully ingested, False otherwise
    """
    sessions_dir = paths.sessions_dir()
    all_sessions = discover()

    for session in all_sessions:
        if session["session_id"] == session_id:
            cli_name = session.get("cli")
            if not cli_name:
                return False

            try:
                provider_class = getattr(providers, cli_name.title())
                provider = provider_class()
                dest_dir = sessions_dir / cli_name
                dest_dir.mkdir(parents=True, exist_ok=True)
                return provider.ingest(session, dest_dir)
            except Exception as e:
                logger.error(f"Error ingesting {cli_name} session {session_id}: {e}")
                return False

    return False


def sync_all(on_progress=None) -> dict[str, tuple[int, int]]:
    """Sync all sessions: discover, ingest, then index.

    Returns:
        {provider_name: (sessions_discovered, sessions_synced)} for each provider
    """
    sessions_dir = paths.sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)

    all_sessions = discover()
    provider_counts = {}
    total_synced = 0
    synced_ids = set()

    for session in all_sessions:
        cli_name = session.get("cli")
        if not cli_name:
            continue

        if cli_name not in provider_counts:
            provider_counts[cli_name] = {"discovered": 0, "synced": 0}

        provider_counts[cli_name]["discovered"] += 1
        session_id = session["session_id"]

        try:
            dest_dir = sessions_dir / cli_name
            provider_class = getattr(providers, cli_name.title())
            provider = provider_class()

            if provider.ingest(session, dest_dir) and session_id not in synced_ids:
                synced_ids.add(session_id)
                total_synced += 1
                provider_counts[cli_name]["synced"] += 1

            if on_progress:
                event = ProgressEvent(
                    provider=cli_name,
                    discovered=0,
                    synced=total_synced,
                    phase="sync",
                )
                on_progress(event)
        except Exception as e:
            logger.warning(f"Failed to ingest session {session_id}: {e}")

    indexed_count = 0
    try:
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts")

            for provider_name in ("claude", "codex", "gemini"):
                provider_dir = sessions_dir / provider_name
                if not provider_dir.exists():
                    continue

                for jsonl_file in provider_dir.glob("*.jsonl"):
                    try:
                        session_id = jsonl_file.stem
                        content = jsonl_file.read_text()
                        if content.strip():
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO sessions
                                (session_id, provider, model)
                                VALUES (?, ?, ?)
                                """,
                                (session_id, provider_name, f"{provider_name}-unknown"),
                            )
                            _index_transcripts(session_id, provider_name, content, conn)
                        indexed_count += 1

                        if on_progress:
                            event = ProgressEvent(
                                provider=provider_name,
                                discovered=0,
                                synced=0,
                                phase="index",
                                indexed=indexed_count,
                            )
                            on_progress(event)
                    except Exception as e:
                        logger.warning(f"Failed to index {jsonl_file}: {e}")

            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to batch index sessions: {e}")

    results = {}
    for cli_name, counts in provider_counts.items():
        results[cli_name] = (counts["discovered"], counts["synced"])

    return results

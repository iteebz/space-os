"""Session sync: discover, ingest, and index provider sessions."""

import logging
from dataclasses import dataclass

from space.lib import paths, providers, store

logger = logging.getLogger(__name__)


def _get_session_identity(session_id: str, conn) -> str | None:
    try:
        row = conn.execute(
            """
            SELECT a.identity FROM spawns s
            JOIN agents a ON s.agent_id = a.agent_id
            WHERE s.session_id = ?
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.debug(f"Failed to get identity for session {session_id}: {e}")
        return None


def _link_session_to_agent(session_id: str, conn) -> None:
    """Link session to agent via spawns table."""
    try:
        row = conn.execute(
            "SELECT agent_id FROM spawns WHERE session_id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE sessions SET agent_id = ? WHERE session_id = ?",
                (row[0], session_id),
            )
    except Exception as e:
        logger.debug(f"Failed to link session {session_id} to agent: {e}")


@dataclass
class ProgressEvent:
    provider: str
    discovered: int
    synced: int
    total_discovered: int = 0
    total_synced: int = 0
    phase: str = "sync"
    indexed: int = 0
    total_indexed: int = 0


def _index_transcripts(session_id: str, provider: str, content: str, conn) -> int:
    from datetime import datetime

    from space.lib import providers

    indexed_count = 0
    rows = []
    identity = _get_session_identity(session_id, conn)

    try:
        provider_class = getattr(providers, provider.title())
    except AttributeError:
        logger.warning(f"Unknown provider: {provider}")
        return 0

    try:
        events = provider_class.parse(content)

        msg_idx = 0
        for msg in events:
            if msg.type != "message":
                continue

            content_data = msg.content
            if not isinstance(content_data, dict):
                continue

            role = content_data.get("role", "").lower()
            if role not in ("user", "assistant"):
                continue

            msg_content = content_data.get("text", "")
            msg_content = str(msg_content).strip()
            if not msg_content:
                continue

            timestamp_str = msg.timestamp
            timestamp_int = 0

            if timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    timestamp_int = int(dt.timestamp())
                except (ValueError, AttributeError):
                    timestamp_int = 0

            rows.append((session_id, msg_idx, provider, role, identity, msg_content, timestamp_int))
            msg_idx += 1
            indexed_count += 1

        if rows:
            conn.executemany(
                """
                INSERT OR REPLACE INTO transcripts
                (session_id, message_index, provider, type, identity, content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

        return indexed_count
    except Exception as e:
        logger.warning(f"Failed to index transcripts for {session_id}: {e}")
        return 0


def discover() -> list[dict]:
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


def index(session_id: str) -> int:
    sessions_dir = paths.sessions_dir()

    for provider_name in ("claude", "codex", "gemini"):
        jsonl_file = sessions_dir / provider_name / f"{session_id}.jsonl"
        if jsonl_file.exists():
            try:
                content = jsonl_file.read_text()
                if content.strip():
                    with store.ensure() as conn:
                        count = _index_transcripts(session_id, provider_name, content, conn)
                        conn.commit()
                        return count
            except Exception as e:
                logger.error(f"Error indexing session {session_id}: {e}")

    return 0


def ingest(session_id: str) -> bool:
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
                            provider_class = getattr(providers, provider_name.title())
                            input_tokens, output_tokens = provider_class.tokens(jsonl_file)

                            conn.execute(
                                """
                                INSERT INTO sessions
                                (session_id, provider, model, input_tokens, output_tokens)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(session_id) DO UPDATE SET
                                    input_tokens = excluded.input_tokens,
                                    output_tokens = excluded.output_tokens
                                """,
                                (
                                    session_id,
                                    provider_name,
                                    f"{provider_name}-unknown",
                                    input_tokens or 0,
                                    output_tokens or 0,
                                ),
                            )
                            _link_session_to_agent(session_id, conn)
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

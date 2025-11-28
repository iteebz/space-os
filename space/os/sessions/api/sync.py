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


@dataclass
class SessionMetadata:
    input_tokens: int
    output_tokens: int
    model: str
    first_timestamp: str | None
    last_timestamp: str | None


def _parse_session_metadata(provider: str, content: str) -> SessionMetadata:
    """Single-pass extraction of tokens, model, and timestamps from JSONL."""
    import io
    import json

    input_total = 0
    output_total = 0
    model = None
    first_ts = None
    last_ts = None

    if provider == "claude":
        for line in io.StringIO(content):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                ts = obj.get("timestamp")
                if ts:
                    if not first_ts:
                        first_ts = ts
                    last_ts = ts

                if isinstance(obj, dict) and "message" in obj:
                    msg = obj["message"]
                    if isinstance(msg, dict):
                        if not model and "model" in msg:
                            model = msg["model"]
                        if "usage" in msg:
                            stop_reason = msg.get("stop_reason")
                            if stop_reason not in ("end_turn", "tool_use"):
                                continue
                            usage = msg["usage"]
                            input_total += usage.get("input_tokens", 0)
                            input_total += usage.get("cache_read_input_tokens", 0)
                            input_total += usage.get("cache_creation_input_tokens", 0)
                            output_total += usage.get("output_tokens", 0)
            except json.JSONDecodeError:
                continue

    elif provider == "codex":
        for line in io.StringIO(content):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                ts = obj.get("timestamp")
                if ts:
                    if not first_ts:
                        first_ts = ts
                    last_ts = ts

                payload = obj.get("payload", {})
                if payload.get("type") == "turn_context" and not model:
                    model = payload.get("model")
                elif payload.get("type") == "token_count" and "info" in payload:
                    info = payload["info"]
                    if isinstance(info, dict) and "total_token_usage" in info:
                        usage = info["total_token_usage"]
                        input_total = usage.get("input_tokens", 0)
                        output_total = usage.get("output_tokens", 0)
            except json.JSONDecodeError:
                continue

    else:
        # Generic timestamp extraction for other providers
        for line in io.StringIO(content):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                ts = obj.get("timestamp")
                if ts:
                    if not first_ts:
                        first_ts = ts
                    last_ts = ts
            except json.JSONDecodeError:
                continue

    return SessionMetadata(
        input_tokens=input_total or 0,
        output_tokens=output_total or 0,
        model=model or f"{provider}-unknown",
        first_timestamp=first_ts,
        last_timestamp=last_ts,
    )


def _index_transcripts(session_id: str, provider: str, content: str, conn) -> int:
    from datetime import datetime

    from space.lib import providers

    indexed_count = 0
    rows = []
    identity = _get_session_identity(session_id, conn)

    try:
        provider_class = providers.get_provider(provider)
    except ValueError:
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

    for provider_name in providers.PROVIDER_NAMES:
        try:
            provider_class = providers.get_provider(provider_name)
            provider = provider_class()
            sessions = provider.discover()
            all_sessions.extend(sessions)
        except Exception as e:
            logger.warning(f"Error discovering {provider_name} sessions: {e}")

    return all_sessions


def _index_session_file(
    session_id: str, provider_name: str, content: str, conn, mtime: float | None = None
) -> int:
    """Index single session: extract metadata, upsert session, link agent, index transcripts."""
    metadata = _parse_session_metadata(provider_name, content)

    conn.execute(
        """
        INSERT INTO sessions
        (session_id, provider, model, input_tokens, output_tokens, source_mtime, first_message_at, last_message_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            model = excluded.model,
            input_tokens = excluded.input_tokens,
            output_tokens = excluded.output_tokens,
            source_mtime = excluded.source_mtime,
            first_message_at = excluded.first_message_at,
            last_message_at = excluded.last_message_at
        """,
        (
            session_id,
            provider_name,
            metadata.model,
            metadata.input_tokens,
            metadata.output_tokens,
            mtime,
            metadata.first_timestamp,
            metadata.last_timestamp,
        ),
    )
    _link_session_to_agent(session_id, conn)
    return _index_transcripts(session_id, provider_name, content, conn)


def index(session_id: str) -> int:
    sessions_dir = paths.sessions_dir()

    for provider_name in providers.PROVIDER_NAMES:
        jsonl_file = sessions_dir / provider_name / f"{session_id}.jsonl"
        if jsonl_file.exists():
            try:
                content = jsonl_file.read_text()
                if content.strip():
                    mtime = jsonl_file.stat().st_mtime
                    with store.ensure() as conn:
                        count = _index_session_file(
                            session_id, provider_name, content, conn, mtime=mtime
                        )
                        conn.commit()
                        return count
            except Exception as e:
                logger.error(f"Error indexing session {session_id}: {e}")

    return 0


def ingest(session_id: str) -> bool:
    sessions_dir = paths.sessions_dir()

    for provider_name in providers.PROVIDER_NAMES:
        try:
            provider_class = providers.get_provider(provider_name)
            provider = provider_class()
            sessions = provider.discover()

            for session in sessions:
                if session["session_id"] == session_id:
                    dest_dir = sessions_dir / provider_name
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    return provider.ingest(session, dest_dir)
        except Exception as e:
            logger.error(f"Error ingesting session {session_id} from {provider_name}: {e}")

    return False


def _sync_sessions(sessions_dir, on_progress=None) -> dict[str, dict]:
    """Discover and ingest sessions from all providers."""
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
            provider_class = providers.get_provider(cli_name)
            provider = provider_class()

            if provider.ingest(session, dest_dir) and session_id not in synced_ids:
                synced_ids.add(session_id)
                total_synced += 1
                provider_counts[cli_name]["synced"] += 1

            if on_progress:
                event = ProgressEvent(
                    provider=cli_name, discovered=0, synced=total_synced, phase="sync"
                )
                on_progress(event)
        except Exception as e:
            logger.warning(f"Failed to ingest session {session_id}: {e}")

    return provider_counts


def _needs_reindex(session_id: str, current_mtime: float, conn) -> bool:
    """Check if session file changed since last index."""
    try:
        row = conn.execute(
            "SELECT source_mtime FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()

        if not row or row[0] is None:
            return True

        last_mtime = row[0]
        return current_mtime > last_mtime
    except Exception:
        return True


def _batch_index_sessions(sessions_dir, on_progress=None) -> int:
    """Index changed JSONL files across providers (diff-based indexing)."""
    indexed_count = 0
    skipped_count = 0

    try:
        with store.ensure() as conn:
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("PRAGMA synchronous = OFF")
            conn.execute("PRAGMA journal_mode = MEMORY")

            for provider_name in providers.PROVIDER_NAMES:
                provider_dir = sessions_dir / provider_name
                if not provider_dir.exists():
                    continue

                files = list(provider_dir.glob("*.jsonl"))

                for jsonl_file in files:
                    try:
                        session_id = jsonl_file.stem
                        current_mtime = jsonl_file.stat().st_mtime

                        # Skip unchanged sessions
                        if not _needs_reindex(session_id, current_mtime, conn):
                            skipped_count += 1
                            continue

                        # Delete only this session's transcripts
                        conn.execute("DELETE FROM transcripts WHERE session_id = ?", (session_id,))

                        # Re-index changed session
                        content = jsonl_file.read_text()
                        if content.strip():
                            _index_session_file(
                                session_id, provider_name, content, conn, mtime=current_mtime
                            )
                        indexed_count += 1

                        if on_progress and indexed_count % 50 == 0:
                            event = ProgressEvent(
                                provider=provider_name,
                                discovered=0,
                                synced=0,
                                phase="index",
                                indexed=indexed_count,
                                total_indexed=len(files),
                            )
                            on_progress(event)
                    except Exception as e:
                        logger.warning(f"Failed to index {jsonl_file}: {e}")

            conn.execute("PRAGMA synchronous = NORMAL")
            conn.commit()
            logger.info(f"Indexed {indexed_count} sessions, skipped {skipped_count} unchanged")
    except Exception as e:
        logger.warning(f"Failed to batch index sessions: {e}")

    return indexed_count


def sync_all(on_progress=None) -> dict[str, tuple[int, int]]:
    sessions_dir = paths.sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)

    provider_counts = _sync_sessions(sessions_dir, on_progress)
    _batch_index_sessions(sessions_dir, on_progress)

    return {
        cli: (counts["discovered"], counts["synced"]) for cli, counts in provider_counts.items()
    }

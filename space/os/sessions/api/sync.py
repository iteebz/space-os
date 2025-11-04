"""Session sync: discover and copy/convert provider sessions to ~/.space/sessions/{provider}/"""

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from space.core.models import Session
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


def _count_tool_uses(content: str) -> int:
    """Count tool_use blocks in session content (JSONL).

    Claude/Codex format: message.content is array of blocks with 'type' field.
    """
    count = 0
    try:
        for line in content.strip().split("\n"):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "message" in obj:
                    msg = obj["message"]
                    if isinstance(msg, dict) and "content" in msg:
                        msg_content = msg["content"]
                        if isinstance(msg_content, list):
                            for block in msg_content:
                                if isinstance(block, dict) and block.get("type") == "tool_use":
                                    count += 1
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    return count


def _extract_timestamps(content: str, provider: str) -> tuple[str | None, str | None]:
    """Extract first and last message timestamps from session content."""
    first_ts = None
    last_ts = None
    try:
        messages = []
        for line in content.strip().split("\n"):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "timestamp" in obj:
                    messages.append(obj["timestamp"])
            except json.JSONDecodeError:
                continue

        if messages:
            first_ts = messages[0]
            last_ts = messages[-1]
    except Exception:
        pass
    return first_ts, last_ts


def _to_jsonl(json_file: Path) -> str:
    """Convert Gemini JSON session to JSONL format.

    Args:
        json_file: Path to Gemini JSON session file

    Returns:
        JSONL string (one JSON object per line)
    """
    try:
        with open(json_file) as f:
            data = json.load(f)

        lines = []
        if isinstance(data, dict) and "messages" in data:
            for msg in data.get("messages", []):
                role = msg.get("role")
                if role not in ("user", "model"):
                    continue
                lines.append(
                    json.dumps(
                        {
                            "role": "assistant" if role == "model" else "user",
                            "content": msg.get("content", ""),
                            "timestamp": msg.get("timestamp"),
                        }
                    )
                )
        return "\n".join(lines) + "\n" if lines else ""
    except (OSError, json.JSONDecodeError):
        return ""


def _index_transcripts(session_id: str, provider: str, content: str) -> int:
    """Index session JSONL content into transcripts table for FTS5 search.

    Parses user and assistant messages from JSONL and populates the transcripts table.
    Tool calls and results are skipped (noise reduction for search).

    Args:
        session_id: Session UUID
        provider: Provider name (claude, codex, gemini)
        content: JSONL content (one JSON object per line)

    Returns:
        Number of messages indexed
    """
    indexed_count = 0

    try:
        from datetime import datetime

        with store.ensure() as conn:
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

                msg_content = str(msg_content)
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

                conn.execute(
                    """
                    INSERT OR REPLACE INTO transcripts
                    (session_id, message_index, provider, role, content, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, msg_idx, provider, role, msg_content, timestamp_int),
                )

                indexed_count += 1

            conn.commit()

    except Exception as e:
        logger.warning(f"Failed to index transcripts for session {session_id}: {e}")

    return indexed_count


def _index_all_sessions(sessions_dir: Path, on_progress=None) -> None:
    """Index ALL JSONL files in ~/.space/sessions/ into sessions + transcripts tables.

    Scans all provider subdirectories and indexes every JSONL file found.
    ~/.space/sessions/ is source of truth. Manual files get indexed too.
    """
    if not sessions_dir.exists():
        return

    total_indexed = 0

    for provider_dir in sessions_dir.iterdir():
        if not provider_dir.is_dir():
            continue

        provider = provider_dir.name
        if provider not in ("claude", "codex", "gemini"):
            continue

        for jsonl_file in provider_dir.glob("*.jsonl"):
            session_id = jsonl_file.stem
            if not session_id:
                continue

            try:
                content = jsonl_file.read_text()
                if not content.strip():
                    continue

                message_count = 0
                for line in content.split("\n"):
                    if line.strip():
                        try:
                            json.loads(line)
                            message_count += 1
                        except json.JSONDecodeError:
                            pass

                tool_count = _count_tool_uses(content)
                first_ts, last_ts = _extract_timestamps(content, provider)

                model_map = {
                    "claude": "claude-opus-4",
                    "codex": "gpt-5",
                    "gemini": "gemini-2.0",
                }
                model = model_map.get(provider, provider)

                session_record = Session(
                    session_id=session_id,
                    model=model,
                    provider=provider,
                    message_count=message_count,
                    tool_count=tool_count,
                    input_tokens=None,
                    output_tokens=None,
                    source_path=str(jsonl_file),
                    first_message_at=first_ts,
                    last_message_at=last_ts,
                )
                mtime = jsonl_file.stat().st_mtime
                size = jsonl_file.stat().st_size
                _insert_session_record(session_record, mtime, size)
                _index_transcripts(session_id, provider, content)

                total_indexed += 1
                if on_progress:
                    event = ProgressEvent(
                        provider=provider,
                        discovered=0,
                        synced=0,
                        phase="index",
                        indexed=total_indexed,
                    )
                    on_progress(event)

            except Exception as e:
                logger.warning(f"Failed to index {jsonl_file}: {e}")


def _insert_session_record(
    session: Session, source_mtime: float | None = None, source_size: int | None = None
) -> None:
    """Insert or update session record in space.db."""
    try:
        conn = store.ensure()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO sessions
            (session_id, model, provider, message_count,
             input_tokens, output_tokens, tool_count, source_path, source_mtime, source_size, first_message_at, last_message_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.model,
                session.provider,
                session.message_count,
                session.input_tokens,
                session.output_tokens,
                session.tool_count,
                session.source_path,
                source_mtime,
                source_size,
                session.first_message_at,
                session.last_message_at,
            ),
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to insert session record for {session.session_id}: {e}")


def sync_provider_sessions(
    session_id: str | None = None,
    verbose: bool = False,
    on_progress=None,
) -> dict[str, tuple[int, int]]:
    """Sync sessions from all providers to ~/.space/sessions/, then index all JSONL files into DB.

    Step 1: Discover and copy from source providers (~/.claude, ~/.codex, ~/.gemini)
            Converts Gemini JSON to JSONL. Tracks source_mtime/source_size to avoid re-copying.

    Step 2: Index ALL JSONL files in ~/.space/sessions/ into sessions + transcripts tables.
            ~/.space/sessions/ is source of truth. Manual files get indexed too.

    Args:
        session_id: If provided, only sync this specific session (resync mode)
        verbose: If True, yield progress messages (not implemented here, use return value)
        on_progress: Optional callback function that receives ProgressEvent

    Returns:
        {provider_name: (sessions_discovered, files_synced)} for each provider
    """
    results = {}
    sessions_dir = paths.sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)

    provider_map = {"claude": "Claude", "codex": "Codex", "gemini": "Gemini"}
    size_threshold = 10 * 1024 * 1024

    total_synced = 0
    total_discovered = 0
    total_processed = 0

    for cli_name, class_name in provider_map.items():
        try:
            provider_class = getattr(providers, class_name)
            provider = provider_class()

            sessions = provider.discover_sessions()
            if not sessions:
                results[cli_name] = (0, 0)
                continue

            total_discovered += len(sessions)
            dest_dir = sessions_dir / cli_name
            dest_dir.mkdir(parents=True, exist_ok=True)

            synced_count = 0
            for _idx, session in enumerate(sessions, 1):
                src_file = Path(session["file_path"])
                if not src_file.exists():
                    continue

                sid = session.get("session_id")

                if session_id and sid != session_id:
                    continue

                total_processed += 1

                if on_progress:
                    event = ProgressEvent(
                        provider=cli_name,
                        discovered=len(sessions),
                        synced=synced_count,
                        total_discovered=total_discovered,
                        total_synced=total_synced + total_processed,
                    )
                    on_progress(event)

                src_mtime = src_file.stat().st_mtime
                file_size = src_file.stat().st_size

                try:
                    with store.ensure() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT source_mtime, source_size FROM sessions WHERE session_id = ?",
                            (sid,),
                        )
                        row = cursor.fetchone()
                        tracked_mtime = row[0] if row and row[0] else 0
                        tracked_size = row[1] if row and row[1] else 0
                except Exception:
                    tracked_mtime = 0
                    tracked_size = 0

                size_changed = file_size != tracked_size
                should_copy = src_mtime > tracked_mtime or size_changed
                should_skip_large = file_size > size_threshold

                try:
                    if should_skip_large:
                        logger.info(
                            f"Skipping {sid}: {file_size / (1024**2):.1f}MB > 10MB threshold"
                        )
                        continue

                    dest_file = dest_dir / f"{sid}.jsonl"

                    if should_copy:
                        if cli_name == "gemini":
                            jsonl_content = _to_jsonl(src_file)
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            dest_file.write_text(jsonl_content)
                        else:
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src_file, dest_file)

                        synced_count += 1

                except (OSError, Exception) as e:
                    logger.warning(f"Failed to process {sid}: {e}")

            results[cli_name] = (len(sessions), synced_count)
            total_synced += synced_count

        except (AttributeError, Exception) as e:
            logger.warning(f"Error syncing {cli_name}: {e}")
            results[cli_name] = (0, 0)

    _index_all_sessions(sessions_dir, on_progress=on_progress)
    return results


def sync_all(on_progress=None) -> dict[str, tuple[int, int]]:
    """Sync all sessions from all providers."""
    return sync_provider_sessions(on_progress=on_progress)


def sync_session(session_id: str, on_progress=None) -> dict[str, tuple[int, int]]:
    """Sync a single session from any provider."""
    return sync_provider_sessions(session_id=session_id, on_progress=on_progress)

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


def _load_sync_state() -> dict:
    """Load sync state tracking {provider}_{session_id}: {mtime, size}."""
    state_file = paths.space_data() / "sync_state.json"
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_sync_state(state: dict) -> None:
    """Save sync state tracking."""
    state_file = paths.space_data() / "sync_state.json"
    paths.space_data().mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))


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


def _insert_session_record(session: Session) -> None:
    """Insert or update session record in space.db."""
    try:
        conn = store.ensure()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO sessions
            (session_id, model, provider, file_path, message_count,
             input_tokens, output_tokens, tool_count, first_message_at, last_message_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.model,
                session.provider,
                session.file_path,
                session.message_count,
                session.input_tokens,
                session.output_tokens,
                session.tool_count,
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
    """Sync sessions from all providers (~/.claude, ~/.codex, ~/.gemini) to ~/.space/sessions/.

    Converts Gemini JSON to JSONL. Only syncs if source is newer/larger than tracked state.
    Tracks by session_id + (mtime, size) to survive format changes.
    Skips files >10MB to avoid memory bloat and excessive storage usage.

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

    sync_state = _load_sync_state()
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

                state_key = f"{cli_name}_{sid}"
                src_mtime = src_file.stat().st_mtime
                file_size = src_file.stat().st_size

                tracked_entry = sync_state.get(state_key, {})
                if isinstance(tracked_entry, (int, float)):
                    tracked_mtime = tracked_entry
                    tracked_size = 0
                else:
                    tracked_mtime = tracked_entry.get("mtime", 0)
                    tracked_size = tracked_entry.get("size", 0)

                size_changed = file_size != tracked_size
                should_copy = src_mtime > tracked_mtime or size_changed
                should_skip_large = file_size > size_threshold

                try:
                    if should_skip_large:
                        logger.info(
                            f"Skipping {sid}: {file_size / (1024**2):.1f}MB > 10MB threshold"
                        )
                        continue

                    if should_copy:
                        if cli_name == "gemini":
                            dest_file = dest_dir / f"{sid}.jsonl"
                            jsonl_content = _to_jsonl(src_file)
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            dest_file.write_text(jsonl_content)
                            content_to_parse = jsonl_content
                        else:
                            dest_file = dest_dir / src_file.name
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src_file, dest_file)
                            content_to_parse = dest_file.read_text()

                        sync_state[state_key] = {"mtime": src_mtime, "size": file_size}
                        synced_count += 1
                    else:
                        dest_file = dest_dir / (
                            f"{sid}.jsonl" if cli_name == "gemini" else src_file.name
                        )
                        if not dest_file.exists():
                            continue
                        content_to_parse = dest_file.read_text()

                    message_count = 0
                    if content_to_parse:
                        for line in content_to_parse.split("\n"):
                            if line.strip():
                                try:
                                    json.loads(line)
                                    message_count += 1
                                except json.JSONDecodeError:
                                    pass
                    tool_count = _count_tool_uses(content_to_parse)
                    first_ts, last_ts = _extract_timestamps(content_to_parse, cli_name)

                    input_tokens, output_tokens = provider.extract_tokens(src_file)

                    model_map = {
                        "claude": "claude-opus-4",
                        "codex": "gpt-5",
                        "gemini": "gemini-2.0",
                    }
                    model = model_map.get(cli_name, cli_name)

                    session_record = Session(
                        session_id=sid,
                        model=model,
                        provider=cli_name,
                        file_path=str(dest_file),
                        message_count=message_count,
                        tool_count=tool_count,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        first_message_at=first_ts,
                        last_message_at=last_ts,
                    )
                    _insert_session_record(session_record)

                except (OSError, Exception) as e:
                    logger.warning(f"Failed to process {sid}: {e}")

            results[cli_name] = (len(sessions), synced_count)
            total_synced += synced_count

        except (AttributeError, Exception) as e:
            logger.warning(f"Error syncing {cli_name}: {e}")
            results[cli_name] = (0, 0)

    _save_sync_state(sync_state)
    return results


def sync_all(on_progress=None) -> dict[str, tuple[int, int]]:
    """Sync all sessions from all providers."""
    return sync_provider_sessions(on_progress=on_progress)


def sync_session(session_id: str, on_progress=None) -> dict[str, tuple[int, int]]:
    """Sync a single session from any provider."""
    return sync_provider_sessions(session_id=session_id, on_progress=on_progress)

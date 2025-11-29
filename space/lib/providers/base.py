"""Base utilities for provider implementations."""

import io
import json
import logging
from pathlib import Path

from space.core.models import SessionMessage

logger = logging.getLogger(__name__)


def parse_spawn_marker(session_file: Path) -> str | None:
    """Extract spawn_marker from session file (auto-detects JSON vs JSONL)."""
    if session_file.suffix == ".json":
        return _parse_marker_json(session_file)
    return _parse_marker_jsonl(session_file)


def _parse_marker_jsonl(session_file: Path) -> str | None:
    """Extract spawn_marker from JSONL file. Scans first 10 lines."""
    try:
        with open(session_file) as f:
            for i, line in enumerate(f):
                if i >= 10:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    marker = _extract_marker_from_dict(data)
                    if marker:
                        return marker
                except json.JSONDecodeError:
                    continue
        return None
    except OSError:
        return None


def _parse_marker_json(session_file: Path) -> str | None:
    """Extract spawn_marker from JSON file (Gemini format)."""
    try:
        with open(session_file) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        for msg in data.get("messages", []):
            if msg.get("type") != "user":
                continue
            content = msg.get("content", "")
            if isinstance(content, str):
                marker = _parse_marker_from_text(content)
                if marker:
                    return marker
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        marker = _parse_marker_from_text(block.get("text", ""))
                        if marker:
                            return marker
            return None
        return None
    except (OSError, json.JSONDecodeError):
        return None


def _extract_marker_from_dict(data: dict) -> str | None:
    """Extract marker from JSONL line (Claude/Codex formats)."""
    # Claude: {"message": {"content": "..."}}
    if "message" in data:
        msg = data["message"]
        if isinstance(msg, dict):
            content = msg.get("content", "")
            if isinstance(content, str):
                marker = _parse_marker_from_text(content)
                if marker:
                    return marker

    # Codex: {"payload": {"content": [{"text": "..."}]}}
    payload = data.get("payload", {})
    if isinstance(payload, dict):
        content = payload.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text", "")
                    if isinstance(text, str):
                        marker = _parse_marker_from_text(text)
                        if marker:
                            return marker

    # Simple: {"content": "..."}
    content = data.get("content", "")
    if isinstance(content, str):
        return _parse_marker_from_text(content)
    return None


def _parse_marker_from_text(text: str) -> str | None:
    """Extract 8-char marker from 'spawn_marker: <marker>' text."""
    if "spawn_marker:" not in text:
        return None
    marker_part = text.split("spawn_marker:")[-1].strip()
    marker = marker_part.split()[0] if marker_part else ""
    return marker if len(marker) == 8 else None


def index_session(session_id: str, provider: str) -> int:
    """Index provider session into database."""
    from space.os.sessions.sync import _index_transcripts

    sessions_dir = Path.home() / ".space" / "sessions" / provider
    jsonl_file = sessions_dir / f"{session_id}.jsonl"

    if not jsonl_file.exists():
        return 0

    try:
        content = jsonl_file.read_text()
        return _index_transcripts(session_id, provider, content)
    except Exception as e:
        logger.error(f"Error indexing {provider} session {session_id}: {e}")
    return 0


def parse_jsonl_file(
    file_path: Path | str,
    parse_line_fn: callable,
    from_offset: int = 0,
) -> list[SessionMessage]:
    """Parse JSONL file using provider-specific line parser."""
    messages = []

    if isinstance(file_path, str):
        file_obj = io.StringIO(file_path)
    else:
        file_path = Path(file_path)
        if not file_path.exists():
            return messages
        file_obj = open(file_path)

    with file_obj:
        for line_num, line in enumerate(file_obj):
            if line_num < from_offset or not line.strip():
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            parsed = parse_line_fn(obj, line_num)
            if parsed:
                if isinstance(parsed, list):
                    messages.extend(parsed)
                else:
                    messages.append(parsed)

    return messages


def ingest_session_copy(
    session: dict,
    dest_dir: Path,
    provider: str,
    extract_session_id_fn: callable,
) -> bool:
    """Ingest session by copying to destination with normalized filename."""
    import shutil

    try:
        src_file = Path(session.get("file_path", ""))

        if not src_file.exists():
            return False

        session_id = extract_session_id_fn(src_file)
        if not session_id:
            logger.warning(f"Could not extract session_id from {src_file}")
            return False

        dest_file = dest_dir / f"{session_id}.jsonl"
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)
        return True
    except Exception as e:
        logger.error(f"Error ingesting {provider} session: {e}")
    return False


def ingest_session_transform(
    session: dict,
    dest_dir: Path,
    provider: str,
    extract_session_id_fn: callable,
    transform_fn: callable,
) -> bool:
    """Ingest session by transforming content and writing to destination."""
    try:
        src_file = Path(session.get("file_path", ""))

        if not src_file.exists():
            return False

        session_id = extract_session_id_fn(src_file)
        if not session_id:
            logger.warning(f"Could not extract session_id from {src_file}")
            return False

        dest_file = dest_dir / f"{session_id}.jsonl"
        dest_dir.mkdir(parents=True, exist_ok=True)
        content = transform_fn(src_file)
        dest_file.write_text(content)
        return bool(content)
    except Exception as e:
        logger.error(f"Error ingesting {provider} session: {e}")
    return False

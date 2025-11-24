"""Base utilities for provider implementations."""

import io
import json
import logging
from pathlib import Path

from space.core.models import SessionMessage

logger = logging.getLogger(__name__)


def index_session(session_id: str, provider: str) -> int:
    """Index provider session into database.

    Args:
        session_id: Session UUID
        provider: Provider name (claude, codex, gemini)

    Returns:
        Number of transcripts indexed
    """
    from space.os.sessions.api.sync import _index_transcripts

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
    """Parse JSONL file using provider-specific line parser.

    Args:
        file_path: Path to JSONL file or raw JSONL string
        parse_line_fn: Function(json_obj, line_num) -> list[SessionMessage]
        from_offset: Line offset to start parsing from

    Returns:
        List of parsed SessionMessage objects
    """
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
    """Ingest session by copying to destination with normalized filename.

    Args:
        session: Session dict with 'file_path' key
        dest_dir: Destination directory
        provider: Provider name (for logging)
        extract_session_id_fn: Function(src_path) -> session_id | None

    Returns:
        True if ingestion succeeded
    """
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
    """Ingest session by transforming content and writing to destination.

    Args:
        session: Session dict with 'file_path' key
        dest_dir: Destination directory
        provider: Provider name (for logging)
        extract_session_id_fn: Function(src_path) -> session_id | None
        transform_fn: Function(src_path) -> transformed_content

    Returns:
        True if ingestion succeeded
    """
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

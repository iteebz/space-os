"""Vault operations: copy provider sessions to ~/.space/chats, normalize Gemini JSON to JSONL."""

import json
import logging
from pathlib import Path

from space.lib import paths

log = logging.getLogger(__name__)


def copy_session_to_vault(cli: str, session_id: str, file_path: str) -> str:
    """
    Copy provider session to ~/.space/chats/{cli}/{session_id}.jsonl.

    For Gemini (JSON): convert to JSONL format.
    For Claude/Codex (JSONL): copy as-is.

    Returns: Path to vault copy (always JSONL).
    """
    vault_dir = paths.chats_dir() / cli
    vault_dir.mkdir(parents=True, exist_ok=True)
    vault_path = vault_dir / f"{session_id}.jsonl"

    source_path = Path(file_path)
    if not source_path.exists():
        log.warning(f"Source file not found: {file_path}")
        return str(vault_path)

    try:
        if cli == "gemini" and file_path.endswith(".json"):
            _copy_gemini_json_to_jsonl(source_path, vault_path)
        else:
            _copy_jsonl(source_path, vault_path)
    except Exception as e:
        log.error(f"Error copying session {cli}/{session_id}: {e}")

    return str(vault_path)


def _copy_jsonl(source: Path, dest: Path) -> None:
    """Copy JSONL file as-is."""
    dest.write_bytes(source.read_bytes())


def _copy_gemini_json_to_jsonl(source: Path, dest: Path) -> None:
    """
    Convert Gemini JSON format to JSONL.

    Preserves: role, content, timestamp, thoughts (reasoning blocks).
    Adds: _provider="gemini" marker.
    """
    try:
        with open(source) as f:
            data = json.load(f)
    except (json.JSONDecodeError, MemoryError) as e:
        log.error(f"Failed to parse Gemini JSON {source}: {e}")
        return

    session_id = data.get("sessionId", source.stem)
    messages = data.get("messages", [])

    with open(dest, "w") as f:
        for msg in messages:
            role = msg.get("role") or msg.get("type", "unknown")
            if role == "model":
                role = "assistant"

            content = msg.get("content", "")
            timestamp = msg.get("timestamp")
            thoughts = msg.get("thoughts")

            normalized = {
                "role": role,
                "content": content,
                "sessionId": session_id,
                "timestamp": timestamp,
                "_provider": "gemini",
            }

            if thoughts:
                normalized["thoughts"] = thoughts

            f.write(json.dumps(normalized) + "\n")

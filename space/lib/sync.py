"""Chat sync: discover and copy/convert provider chats to ~/.space/chats/{provider}/"""

import json
import shutil
from pathlib import Path

from space.lib import paths, providers


def _load_sync_state() -> dict:
    """Load sync state tracking {provider}_{session_id}: mtime."""
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


def _gemini_json_to_jsonl(json_file: Path) -> str:
    """Convert Gemini JSON chat to JSONL format.

    Args:
        json_file: Path to Gemini JSON chat file

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


def sync_provider_chats(verbose: bool = False) -> dict[str, tuple[int, int]]:
    """Sync chats from all providers (~/.claude, ~/.codex, ~/.gemini) to ~/.space/chats/.

    Converts Gemini JSON to JSONL. Only syncs if source is newer than tracked state.
    Tracks by session_id + mtime to survive format changes.

    Args:
        verbose: If True, yield progress messages (not implemented here, use return value)

    Returns:
        {provider_name: (sessions_discovered, files_synced)} for each provider
    """
    results = {}
    chats_dir = paths.chats_dir()
    chats_dir.mkdir(parents=True, exist_ok=True)

    sync_state = _load_sync_state()
    provider_map = {"claude": "Claude", "codex": "Codex", "gemini": "Gemini"}

    for cli_name, class_name in provider_map.items():
        try:
            provider_class = getattr(providers, class_name)
            provider = provider_class()

            sessions = provider.discover_sessions()
            if not sessions:
                results[cli_name] = (0, 0)
                continue

            dest_dir = chats_dir / cli_name
            dest_dir.mkdir(parents=True, exist_ok=True)

            synced_count = 0
            for session in sessions:
                src_file = Path(session["file_path"])
                if not src_file.exists():
                    continue

                session_id = session.get("session_id")
                state_key = f"{cli_name}_{session_id}"
                src_mtime = src_file.stat().st_mtime
                tracked_mtime = sync_state.get(state_key, 0)

                should_sync = src_mtime > tracked_mtime

                if not should_sync:
                    continue

                try:
                    if cli_name == "gemini":
                        dest_file = dest_dir / f"{session_id}.jsonl"
                        jsonl_content = _gemini_json_to_jsonl(src_file)
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        dest_file.write_text(jsonl_content)
                    else:
                        dest_file = dest_dir / src_file.name
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest_file)

                    sync_state[state_key] = src_mtime
                    synced_count += 1
                except (OSError, Exception):
                    pass

            results[cli_name] = (len(sessions), synced_count)
        except (AttributeError, Exception):
            results[cli_name] = (0, 0)

    _save_sync_state(sync_state)
    return results

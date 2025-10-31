"""Chat sync: discover and copy/convert provider chats to ~/.space/chats/{provider}/"""

import json
import logging
import shutil
from pathlib import Path

from space.core import db
from space.core.models import Chat
from space.lib import paths, providers

logger = logging.getLogger(__name__)


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
    """Count tool_use blocks in chat content (JSONL).
    
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
    """Extract first and last message timestamps from chat content."""
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


def _insert_chat_record(chat: Chat) -> None:
    """Insert or update chat record in space.db."""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO chats
            (session_id, provider, identity, task_id, file_path, message_count,
             tools_used, input_tokens, output_tokens, first_message_at, last_message_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat.session_id,
                chat.provider,
                chat.identity,
                chat.task_id,
                chat.file_path,
                chat.message_count,
                chat.tools_used,
                chat.input_tokens,
                chat.output_tokens,
                chat.first_message_at,
                chat.last_message_at,
                chat.created_at or None,
            ),
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to insert chat record for {chat.session_id}: {e}")


def _link_chat_to_task(chat: Chat, cli_name: str) -> None:
    """Link chat to task based on identity and created_at timestamp.
    
    Finds task with matching agent_id (via identity) and recent start time.
    """
    try:
        from space.os.spawn import api as spawn_api
        
        if not chat.identity:
            return
        
        agent = spawn_api.get_agent(chat.identity)
        if not agent:
            return
        
        conn = db.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT task_id, started_at FROM tasks 
            WHERE agent_id = ? AND status = 'running'
            ORDER BY started_at DESC LIMIT 1
            """,
            (agent.agent_id,)
        )
        row = cursor.fetchone()
        if not row:
            return
        
        task_id, started_at = row
        if started_at and chat.created_at:
            try:
                from datetime import datetime, timedelta
                task_start = datetime.fromisoformat(started_at)
                chat_start = datetime.fromisoformat(chat.created_at)
                if abs((chat_start - task_start).total_seconds()) < 60:
                    cursor.execute(
                        "UPDATE chats SET task_id = ? WHERE session_id = ?",
                        (task_id, chat.session_id)
                    )
                    conn.commit()
            except (ValueError, TypeError):
                pass
    except Exception as e:
        logger.debug(f"Failed to link chat {chat.session_id} to task: {e}")


def sync_provider_chats(session_id: str | None = None, verbose: bool = False) -> dict[str, tuple[int, int]]:
    """Sync chats from all providers (~/.claude, ~/.codex, ~/.gemini) to ~/.space/chats/.

    Converts Gemini JSON to JSONL. Only syncs if source is newer/larger than tracked state.
    Tracks by session_id + (mtime, size) to survive format changes.
    Skips Gemini files >50MB to avoid memory bloat.
    Links chats to tasks based on identity and timestamp proximity.

    Args:
        session_id: If provided, only sync this specific session (resync mode)
        verbose: If True, yield progress messages (not implemented here, use return value)

    Returns:
        {provider_name: (sessions_discovered, files_synced)} for each provider
    """
    results = {}
    chats_dir = paths.chats_dir()
    chats_dir.mkdir(parents=True, exist_ok=True)

    sync_state = _load_sync_state()
    provider_map = {"claude": "Claude", "codex": "Codex", "gemini": "Gemini"}
    size_threshold = 50 * 1024 * 1024

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

                sid = session.get("session_id")
                
                if session_id and sid != session_id:
                    continue
                
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
                should_skip_large = cli_name == "gemini" and file_size > size_threshold

                try:
                    if should_skip_large:
                        logger.info(
                            f"Skipping {sid}: {file_size / (1024**2):.1f}MB > 50MB threshold"
                        )
                        continue

                    if should_copy:
                        if cli_name == "gemini":
                            dest_file = dest_dir / f"{sid}.jsonl"
                            jsonl_content = _gemini_json_to_jsonl(src_file)
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
                        dest_file = dest_dir / (f"{sid}.jsonl" if cli_name == "gemini" else src_file.name)
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
                    tools_used = _count_tool_uses(content_to_parse)
                    first_ts, last_ts = _extract_timestamps(content_to_parse, cli_name)
                    
                    input_tokens, output_tokens = provider.extract_tokens(src_file)

                    chat = Chat(
                        session_id=sid,
                        provider=cli_name,
                        file_path=str(dest_file),
                        message_count=message_count,
                        tools_used=tools_used,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        first_message_at=first_ts,
                        last_message_at=last_ts,
                    )
                    _insert_chat_record(chat)
                    
                    _link_chat_to_task(chat, cli_name)

                except (OSError, Exception) as e:
                    logger.warning(f"Failed to process {sid}: {e}")

            results[cli_name] = (len(sessions), synced_count)
        except (AttributeError, Exception) as e:
            logger.warning(f"Error syncing {cli_name}: {e}")
            results[cli_name] = (0, 0)

    _save_sync_state(sync_state)
    return results

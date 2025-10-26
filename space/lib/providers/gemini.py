"""Gemini provider: chat discovery + message parsing + spawning."""

import json
import subprocess
from pathlib import Path


class Gemini:
    """Gemini provider: chat discovery + message parsing + spawning."""

    def __init__(self):
        self.tmp_dir = Path.home() / ".gemini" / "tmp"

    def discover_sessions(self) -> list[dict]:
        """Discover Gemini chat sessions from actual chat files and logs.json index."""
        sessions = []
        if not self.tmp_dir.exists():
            return sessions

        for project_dir in self.tmp_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_hash = project_dir.name
            chats_dir = project_dir / "chats"
            logs_file = project_dir / "logs.json"

            # Index sessions from logs.json (fast, metadata only)
            session_metadata = {}
            if logs_file.exists():
                try:
                    with open(logs_file) as f:
                        logs = json.load(f)
                    # Dedupe by sessionId (logs.json has one entry per message)
                    for entry in logs:
                        sid = entry.get("sessionId")
                        if sid and sid not in session_metadata:
                            session_metadata[sid] = {
                                "timestamp": entry.get("timestamp"),
                                "first_message": entry.get("message", ""),
                            }
                except (OSError, json.JSONDecodeError, MemoryError):
                    # Skip if too large or corrupted
                    pass

            # Discover actual chat files (ground truth)
            if chats_dir.exists():
                for chat_file in chats_dir.glob("session-*.json"):
                    file_size = chat_file.stat().st_size

                    try:
                        with open(chat_file) as f:
                            chat_data = json.load(f)
                        session_id = chat_data.get("sessionId")
                        if not session_id:
                            continue

                        sessions.append(
                            {
                                "cli": "gemini",
                                "session_id": session_id,
                                "file_path": str(chat_file),
                                "project_hash": project_hash,
                                "created_at": chat_file.stat().st_ctime,
                                "start_time": chat_data.get("startTime"),
                                "last_updated": chat_data.get("lastUpdated"),
                                "message_count": len(chat_data.get("messages", [])),
                                "file_size": file_size,
                                "first_message": session_metadata.get(session_id, {}).get(
                                    "first_message", ""
                                ),
                            }
                        )
                    except (OSError, json.JSONDecodeError, MemoryError):
                        # Gracefully skip malformed/huge files; they'll work on retry
                        # or with streaming parser in future
                        continue

        return sessions

    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
        """
        Parse messages from Gemini JSONL (normalized in vault).
        
        Reads from ~/.space/chats/gemini/*.jsonl (converted from provider JSON by vault).
        from_offset is byte offset (like Claude/Codex).
        """
        messages = []
        try:
            with open(file_path, "rb") as f:
                f.seek(from_offset)
                for line in f:
                    if not line.strip():
                        continue
                    offset = f.tell() - len(line)
                    data = json.loads(line)
                    role = data.get("role")
                    if role not in ("user", "assistant"):
                        continue
                    
                    messages.append(
                        {
                            "message_id": None,
                            "role": role,
                            "content": data.get("content", ""),
                            "timestamp": data.get("timestamp"),
                            "byte_offset": offset,
                        }
                    )
        except (OSError, json.JSONDecodeError):
            pass
        return messages

    def spawn(self, identity: str, task: str | None = None) -> str:
        """Spawn Gemini agent."""
        if task:
            result = subprocess.run(
                [
                    "gemini",
                    "-p",
                    task,
                    "--yolo",
                ],
                capture_output=True,
                text=True,
            )
            return result.stdout

        from space.core.spawn.api import launch_agent

        launch_agent(identity)
        return ""

    def ping(self, identity: str) -> bool:
        """Check if Gemini agent is alive."""
        try:
            from space.core.spawn import api as spawn_api

            return spawn_api.get_agent(identity) is not None
        except Exception:
            return False

    def list_agents(self) -> list[str]:
        """List all active agents."""
        try:
            from space.core.spawn import api as spawn_api

            return spawn_api.list_agents()
        except Exception:
            return []

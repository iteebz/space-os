"""Gemini provider: chat discovery and message parsing."""

import json
import logging
from pathlib import Path

from space.core.protocols import Provider

logger = logging.getLogger(__name__)


class Gemini(Provider):
    """Gemini provider: chat discovery and message parsing."""

    def __init__(self):
        self.tmp_dir = Path.home() / ".gemini" / "tmp"

    @staticmethod
    def allowed_tools() -> list[str]:
        """Return allowed tools for Gemini."""
        return [
            "Edit",
            "FindFiles",
            "GoogleSearch",
            "ReadFile",
            "ReadFolder",
            "ReadManyFiles",
            "SearchText",
            "Shell",
            "WebFetch",
            "WriteFile",
        ]

    @staticmethod
    def launch_args(has_prompt: bool = False) -> list[str]:
        """Return launch arguments for Gemini."""
        allowed = Gemini.allowed_tools()
        args = ["--allowed-tools"] + allowed
        if has_prompt:
            args.append("--prompt-interactive")
        return args

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
                except (OSError, json.JSONDecodeError, MemoryError) as e:
                    logger.error(f"Error processing logs.json for project {project_hash}: {e}")

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
                    except (OSError, json.JSONDecodeError, MemoryError) as e:
                        logger.error(f"Error parsing Gemini chat file {chat_file}: {e}")
                        continue

        return sessions

    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
        """
        Parse messages from Gemini JSON or JSONL.

        Handles both:
        - Raw JSON format from provider (single JSON object with messages array)
        - JSONL format from vault (one JSON object per line)
        from_offset is byte offset (like Claude/Codex).
        """
        messages = []
        try:
            with open(file_path, "rb") as f:
                f.seek(from_offset)
                content = f.read().decode("utf-8")

            if content.strip().startswith("[") or content.strip().startswith("{"):
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and "messages" in data:
                        for msg in data.get("messages", []):
                            role = msg.get("role")
                            if role not in ("user", "model"):
                                continue
                            messages.append(
                                {
                                    "message_id": None,
                                    "role": "assistant" if role == "model" else "user",
                                    "content": msg.get("content", ""),
                                    "timestamp": msg.get("timestamp"),
                                    "byte_offset": 0,
                                }
                            )
                        return messages
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Error parsing Gemini JSON content from {file_path}: {e}")

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
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Gemini messages from {file_path}: {e}")
        return messages

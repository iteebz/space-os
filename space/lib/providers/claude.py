"""Claude provider: chat discovery and message parsing."""

import json
import logging
from pathlib import Path

from space.core.protocols import Provider

logger = logging.getLogger(__name__)


class Claude(Provider):
    """Claude provider: chat discovery and message parsing."""

    def __init__(self):
        self.chats_dir = Path.home() / ".claude" / "projects"

    @staticmethod
    def allowed_tools() -> list[str]:
        """Return allowed tools for Claude."""
        return [
            "Bash",
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Grep",
            "Glob",
            "WebSearch",
            "WebFetch",
            "LS",
        ]

    @staticmethod
    def launch_args() -> list[str]:
        """Return launch arguments for Claude."""
        disallowed = [
            "NotebookRead",
            "NotebookEdit",
            "Task",
            "TodoWrite",
        ]
        return ["--dangerously-skip-permissions", "--disallowedTools", ",".join(disallowed)]

    def discover_sessions(self) -> list[dict]:
        """Discover Claude chat sessions."""
        sessions = []
        if not self.chats_dir.exists():
            return sessions

        for jsonl in self.chats_dir.rglob("*.jsonl"):
            sessions.append(
                {
                    "cli": "claude",
                    "session_id": jsonl.stem,
                    "file_path": str(jsonl),
                    "created_at": jsonl.stat().st_ctime,
                }
            )
        return sessions

    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
        """Parse messages from Claude JSONL."""
        messages = []
        try:
            with open(file_path, "rb") as f:
                f.seek(from_offset)
                for line in f:
                    if not line.strip():
                        continue
                    offset = f.tell() - len(line)
                    data = json.loads(line)
                    role = data.get("type")
                    if role not in ("user", "assistant", "tool"):
                        continue
                    message_obj = data.get("message", {})
                    content = ""
                    if isinstance(message_obj, dict):
                        content_raw = message_obj.get("content", "")
                        if isinstance(content_raw, list):
                            content = "\n".join(
                                item.get("text", "")
                                for item in content_raw
                                if isinstance(item, dict) and item.get("type") == "text"
                            )
                        else:
                            content = content_raw
                    else:
                        content = message_obj

                    msg = {
                        "message_id": data.get("uuid"),
                        "role": role,
                        "content": content,
                        "timestamp": data.get("timestamp"),
                        "cwd": data.get("cwd"),
                        "byte_offset": offset,
                    }
                    if role == "tool":
                        msg["tool_type"] = "tool_result"
                    messages.append(msg)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Claude messages from {file_path}: {e}")
        return messages

    def extract_tokens(self, file_path: Path) -> tuple[int | None, int | None]:
        """Extract input and output tokens from Claude JSONL.

        Claude stores tokens in message.usage.{input,output}_tokens
        """
        input_total = 0
        output_total = 0
        found_any = False
        try:
            with open(file_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and "message" in obj:
                            msg = obj["message"]
                            if isinstance(msg, dict) and "usage" in msg:
                                usage = msg["usage"]
                                inp = usage.get("input_tokens", 0)
                                out = usage.get("output_tokens", 0)
                                if inp or out:
                                    input_total += inp
                                    output_total += out
                                    found_any = True
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.error(f"Error extracting Claude tokens from {file_path}: {e}")
        return (input_total if found_any else None, output_total if found_any else None)

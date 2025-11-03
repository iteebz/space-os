"""Codex provider: chat discovery and message parsing."""

import json
import logging
from pathlib import Path

from space.core.protocols import Provider

logger = logging.getLogger(__name__)


class Codex(Provider):
    """Codex provider: chat discovery and message parsing.

    Codex supports two models: gpt-5-codex (optimized for coding) and gpt-5 (general).
    Reasoning effort defaults to low and is configured via codex config, not CLI args.
    """

    def __init__(self):
        self.sessions_dir = Path.home() / ".codex" / "sessions"

    @staticmethod
    def launch_args() -> list[str]:
        """Return launch arguments for Codex."""
        return ["--dangerously-bypass-approvals-and-sandbox"]

    def discover_chats(self) -> list[dict]:
        """Discover Codex chat sessions."""
        sessions = []
        if not self.sessions_dir.exists():
            return sessions

        for jsonl in self.sessions_dir.rglob("*.jsonl"):
            sessions.append(
                {
                    "cli": "codex",
                    "session_id": jsonl.stem,
                    "file_path": str(jsonl),
                    "created_at": jsonl.stat().st_ctime,
                }
            )
        return sessions

    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
        """Parse messages from Codex JSONL."""
        messages = []
        try:
            with open(file_path, "rb") as f:
                f.seek(from_offset)
                for line in f:
                    if not line.strip():
                        continue
                    offset = f.tell() - len(line)
                    data = json.loads(line)
                    msg_type = data.get("type")
                    payload = data.get("payload", {})

                    if msg_type == "response_item":
                        role = payload.get("role")
                        if role not in ("user", "assistant"):
                            continue

                        content_list = payload.get("content", [])
                        content = ""
                        if isinstance(content_list, list):
                            content = "\n".join(
                                item.get("text", "")
                                for item in content_list
                                if isinstance(item, dict) and item.get("type") == "input_text"
                            )

                        else:
                            content = content_list

                        msg = {
                            "message_id": payload.get("id"),
                            "role": role,
                            "content": content,
                            "timestamp": data.get("timestamp"),
                            "cwd": payload.get("cwd"),
                            "byte_offset": offset,
                        }
                        messages.append(msg)
                    elif msg_type in ("tool_call", "tool_result"):
                        content_list = payload.get("content", [])
                        content = ""
                        if isinstance(content_list, list):
                            content = "\n".join(
                                item.get("text", "")
                                for item in content_list
                                if isinstance(item, dict) and item.get("type") == "input_text"
                            )
                        else:
                            content = content_list

                        msg = {
                            "message_id": payload.get("id"),
                            "role": "tool",
                            "content": content,
                            "timestamp": data.get("timestamp"),
                            "cwd": payload.get("cwd"),
                            "tool_type": msg_type,
                            "byte_offset": offset,
                        }
                        messages.append(msg)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Codex messages from {file_path}: {e}")
        return messages

    def extract_tokens(self, file_path: Path) -> tuple[int | None, int | None]:
        """Extract input and output tokens from Codex JSONL.

        Codex stores tokens in token_count events under info.total_token_usage
        Returns the most recent token counts found.
        """
        input_tokens = None
        output_tokens = None
        try:
            with open(file_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and "payload" in obj:
                            payload = obj["payload"]
                            if payload.get("type") == "token_count" and "info" in payload:
                                info = payload["info"]
                                if isinstance(info, dict) and "total_token_usage" in info:
                                    usage = info["total_token_usage"]
                                    input_tokens = usage.get("input_tokens")
                                    output_tokens = usage.get("output_tokens")
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.error(f"Error extracting Codex tokens from {file_path}: {e}")
        return (input_tokens, output_tokens)

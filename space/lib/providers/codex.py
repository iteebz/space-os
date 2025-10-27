"""Codex provider: chat discovery + message parsing + spawning."""

import json
import logging
import subprocess
from pathlib import Path

from space.core.protocols import Provider

logger = logging.getLogger(__name__)


class Codex(Provider):
    """Codex provider: chat discovery + message parsing + spawning.

    Codex supports two models: gpt-5-codex (optimized for coding) and gpt-5 (general).
    Reasoning effort defaults to low and is configured via codex config, not CLI args.
    """

    def __init__(self):
        self.sessions_dir = Path.home() / ".codex" / "sessions"

    @staticmethod
    def launch_args() -> list[str]:
        """Return launch arguments for Codex."""
        return ["--dangerously-bypass-approvals-and-sandbox"]

    def discover_sessions(self) -> list[dict]:
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

    def spawn(self, identity: str, task: str | None = None) -> str:
        """Spawn Codex agent."""
        if task:
            result = subprocess.run(
                [
                    "codex",
                    "exec",
                    task,
                    "--full-auto",
                    "--skip-git-repo-check",
                ],
                capture_output=True,
                text=True,
            )
            return result.stdout

        from space.os.spawn.api import spawn_agent

        spawn_agent(identity)
        return ""

    def ping(self, identity: str) -> bool:
        """Check if Codex agent is alive."""
        try:
            from space.os.spawn import api as spawn_api

            return spawn_api.get_agent(identity) is not None
        except Exception as e:
            logger.error(f"Error pinging Codex agent {identity}: {e}")
            return False

    def list_agents(self) -> list[str]:
        """List all active agents."""
        try:
            from space.os.spawn import api as spawn_api

            return spawn_api.list_agents()
        except Exception as e:
            logger.error(f"Error listing Codex agents: {e}")
            return []

"""Claude provider: chat discovery + message parsing + spawning."""

import json
import subprocess
from pathlib import Path

from space import config


class Claude:
    """Claude provider: chat discovery + message parsing + spawning."""

    def __init__(self):
        self.chats_dir = Path.home() / ".claude" / "projects"

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
        except (OSError, json.JSONDecodeError):
            pass
        return messages

    def spawn(self, role: str, task: str | None = None) -> str:
        """Spawn Claude agent."""
        if task:
            config.init_config()
            cfg = config.load_config()

            if role not in cfg["roles"]:
                raise ValueError(f"Unknown role: {role}")

            role_cfg = cfg["roles"][role]
            base_agent = role_cfg["base_agent"]
            agent_cfg = cfg.get("agents", {}).get(base_agent)
            if not agent_cfg:
                raise ValueError(f"Agent not configured: {base_agent}")

            command = agent_cfg.get("command")
            result = subprocess.run(
                [
                    command,
                    "-p",
                    task,
                    "--dangerously-skip-permissions",
                    "--disallowedTools",
                    "Task",
                ],
                capture_output=True,
                text=True,
            )
            return result.stdout

        from space.core.spawn.api import launch_agent

        launch_agent(role)
        return ""

    def ping(self, identity: str) -> bool:
        """Check if Claude agent is alive."""
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

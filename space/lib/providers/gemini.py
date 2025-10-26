"""Gemini provider: chat discovery + message parsing + spawning."""

import json
import subprocess
from pathlib import Path

from space import config


class Gemini:
    """Gemini provider: chat discovery + message parsing + spawning."""

    def __init__(self):
        self.tmp_dir = Path.home() / ".gemini" / "tmp"

    def discover_sessions(self) -> list[dict]:
        """Discover Gemini chat sessions."""
        sessions = []
        if not self.tmp_dir.exists():
            return sessions

        for subdir in self.tmp_dir.iterdir():
            if not subdir.is_dir():
                continue
            for json_file in subdir.glob("session-*.json"):
                sessions.append({
                    "cli": "gemini",
                    "session_id": json_file.stem,
                    "file_path": str(json_file),
                    "created_at": json_file.stat().st_ctime,
                })
        return sessions

    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
        """Parse messages from Gemini JSON."""
        messages = []
        try:
            with open(file_path) as f:
                data = json.load(f)

            for i, msg in enumerate(data.get("messages", [])):
                if i < from_offset:
                    continue
                role = msg.get("role") or msg.get("type")
                if role not in ("user", "model", "assistant"):
                    continue
                if role == "model":
                    role = "assistant"
                messages.append({
                    "role": role,
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp"),
                    "message_index": i,
                })
        except (OSError, json.JSONDecodeError):
            pass
        return messages

    def spawn(self, role: str, task: str | None = None) -> str:
        """Spawn Gemini agent."""
        config.init_config()
        cfg = config.load_config()

        if role not in cfg["roles"]:
            raise ValueError(f"Unknown role: {role}")

        role_cfg = cfg["roles"][role]
        base_agent = role_cfg["base_agent"]

        agent_cfg = cfg.get("agents", {}).get(base_agent)
        if not agent_cfg:
            raise ValueError(f"Agent not configured: {base_agent}")

        model = agent_cfg.get("model")
        command = agent_cfg.get("command")

        if task:
            result = subprocess.run(
                [command, "-p", task],
                capture_output=True,
                text=True,
            )
            return result.stdout

        from space.core.spawn import spawn as spawn_launcher

        constitution = role.split("-")[0] if "-" in role else role
        spawn_launcher.launch_agent(
            constitution=constitution,
            role=role,
            base_agent=base_agent,
            model=model,
        )
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

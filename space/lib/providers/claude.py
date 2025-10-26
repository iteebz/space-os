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
            sessions.append({
                "cli": "claude",
                "session_id": jsonl.stem,
                "file_path": str(jsonl),
                "created_at": jsonl.stat().st_ctime,
            })
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
                    if role not in ("user", "assistant"):
                        continue
                    messages.append({
                        "role": role,
                        "content": data.get("message", ""),
                        "timestamp": data.get("timestamp"),
                        "byte_offset": offset,
                    })
        except (OSError, json.JSONDecodeError):
            pass
        return messages

    def spawn(self, role: str, task: str | None = None) -> str:
        """Spawn Claude agent."""
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
                [
                    command,
                    "-p",
                    task,
                    "--allowedTools",
                    "Bash Edit Read Glob Grep LS Write WebFetch",
                ],
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

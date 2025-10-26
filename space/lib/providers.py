import subprocess
from pathlib import Path

from space import config


class Agent:
    """Wrapper for spawning and managing external LLM agents (Claude, Codex, Gemini)."""

    def __init__(
        self,
        name: str,
        chats_dir: Path,
        task_args,
    ):
        self.name = name
        self.chats_dir = chats_dir
        self.task_args = task_args

    def spawn(self, role: str, task: str | None = None) -> str:
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
                self.task_args(command, task),
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

    def ping(self, agent_identity: str) -> bool:
        try:
            from space.core.spawn import api as spawn_api

            return spawn_api.get_agent(agent_identity) is not None
        except Exception:
            return False

    def status(self, agent_identity: str) -> dict:
        """Get agent status: health, spawns, tasks, activity."""
        try:
            from space.core.spawn import api as spawn_api

            agent = spawn_api.get_agent(agent_identity)
            if not agent:
                return {"state": "not_found"}

            stats = spawn_api.agent_stats(agent.agent_id)
            return {
                "state": "archived" if agent.archived_at else "active",
                "spawns": stats.get("task_count", 0),
                "tasks": {
                    "pending": stats.get("pending", 0),
                    "running": stats.get("running", 0),
                    "completed": stats.get("completed", 0),
                },
                "last_activity": stats.get("last_activity"),
                "created_at": agent.created_at,
            }
        except Exception as e:
            return {"error": str(e)}

    def health(self, agent_identity: str) -> str:
        """Get agent health: healthy, idle, or archived."""
        try:
            status = self.status(agent_identity)
            if "error" in status or status.get("state") == "not_found":
                return "dead"
            if status.get("state") == "archived":
                return "archived"
            if status.get("tasks", {}).get("running", 0) > 0:
                return "healthy"
            return "idle"
        except Exception:
            return "dead"

    def list_agents(self) -> list[str]:
        """List all active agents from registry."""
        try:
            from space.core.spawn import api as spawn_api

            return spawn_api.list_agents()
        except Exception:
            return []


claude = Agent(
    name="claude",
    chats_dir=Path.home() / ".claude" / "projects",
    task_args=lambda cmd, task: [
        cmd,
        "-p",
        task,
        "--allowedTools",
        "Bash Edit Read Glob Grep LS Write WebFetch",
    ],
)

codex = Agent(
    name="codex",
    chats_dir=Path.home() / ".codex" / "sessions",
    task_args=lambda cmd, task: [cmd, "exec", task, "--skip-git-repo-check"],
)

gemini = Agent(
    name="gemini",
    chats_dir=Path.home() / ".gemini" / "tmp",
    task_args=lambda cmd, task: [cmd, "-p", task],
)

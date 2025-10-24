import json
import subprocess
from pathlib import Path
from typing import Callable

from space.os import config
from space.os.models import ChatMessage


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        text_field = content.get("text") or content.get("content") or ""
        if isinstance(text_field, list):
            return " ".join(
                str(t.get("text", "") if isinstance(t, dict) else t) for t in text_field
            ).strip()
        return str(text_field)
    if isinstance(content, list):
        return " ".join(
            str(item.get("text", "") if isinstance(item, dict) else item) for item in content
        ).strip()
    return str(content) if content else ""


class Agent:
    def __init__(
        self,
        name: str,
        chats_dir: Path,
        chats_loader: Callable[[Path], list[ChatMessage]],
        task_args: Callable[[str, str], list[str]],
    ):
        self.name = name
        self.chats_dir = chats_dir
        self.chats_loader = chats_loader
        self.task_args = task_args

    def chats(self) -> list[ChatMessage]:
        """Extract chat history from CLI sessions."""
        if not self.chats_dir.exists():
            return []
        return self.chats_loader(self.chats_dir)

    def spawn(self, identity: str, task: str | None = None) -> str:
        config.init_config()
        cfg = config.load_config()

        if identity not in cfg["roles"]:
            raise ValueError(f"Unknown identity: {identity}")

        role_cfg = cfg["roles"][identity]
        base_identity = role_cfg["base_identity"]

        agent_cfg = cfg.get("agents", {}).get(base_identity)
        if not agent_cfg:
            raise ValueError(f"Agent not configured: {base_identity}")

        model = agent_cfg.get("model")
        command = agent_cfg.get("command")

        if task:
            result = subprocess.run(
                self.task_args(command, task),
                capture_output=True,
                text=True,
            )
            return result.stdout

        from space.os.core.spawn import spawn as spawn_launcher

        role = identity.split("-")[0] if "-" in identity else identity
        spawn_launcher.launch_agent(
            role=role,
            identity=identity,
            base_identity=base_identity,
            model=model,
        )
        return ""


def _load_claude_chats(chats_dir: Path) -> list[ChatMessage]:
    msgs = []
    for project_dir in chats_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        raw = json.loads(line)
                        role = raw.get("type")
                        if role not in ("user", "assistant"):
                            continue
                        text = _extract_text(raw.get("message"))
                        if not text:
                            continue
                        msgs.append(
                            ChatMessage(
                                id=0,
                                cli="claude",
                                model=None,
                                session_id=str(jsonl_file.stem),
                                timestamp=raw.get("timestamp"),
                                identity=None,
                                role=role,
                                text=text,
                            )
                        )
            except (OSError, json.JSONDecodeError):
                continue
    return msgs


def _load_codex_chats(sessions_dir: Path) -> list[ChatMessage]:
    msgs = []
    model_cache = {}

    for jsonl_file in sessions_dir.rglob("*.jsonl"):
        if jsonl_file not in model_cache:
            model = None
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        raw = json.loads(line)
                        if raw.get("type") == "turn_context":
                            model = raw.get("payload", {}).get("model")
                            break
            except (OSError, json.JSONDecodeError):
                pass
            model_cache[jsonl_file] = model

        try:
            with open(jsonl_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    raw = json.loads(line)
                    if raw.get("type") != "response_item":
                        continue
                    payload = raw.get("payload", {})
                    role = payload.get("role")
                    if role not in ("user", "assistant"):
                        continue
                    text = _extract_text(payload.get("content"))
                    if not text:
                        continue
                    msgs.append(
                        ChatMessage(
                            id=0,
                            cli="codex",
                            model=model_cache[jsonl_file],
                            session_id=str(jsonl_file.stem),
                            timestamp=raw.get("timestamp"),
                            identity=None,
                            role=role,
                            text=text,
                        )
                    )
        except (OSError, json.JSONDecodeError):
            continue

    return msgs


def _load_gemini_chats(gemini_dir: Path) -> list[ChatMessage]:
    msgs = []
    for subdir in gemini_dir.iterdir():
        if not subdir.is_dir():
            continue
        for json_file in subdir.glob("*.json"):
            if json_file.name == "logs.json":
                continue

            try:
                with open(json_file) as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        continue

                    session_id = data.get("sessionId", str(json_file.stem))
                    for raw in data.get("messages", []):
                        role = raw.get("role") or raw.get("type")
                        if role not in ("user", "model", "assistant"):
                            continue
                        if role == "model":
                            role = "assistant"
                        text = _extract_text(raw.get("content"))
                        if not text:
                            continue
                        msgs.append(
                            ChatMessage(
                                id=0,
                                cli="gemini",
                                model=None,
                                session_id=session_id,
                                timestamp=raw.get("timestamp"),
                                identity=None,
                                role=role,
                                text=text,
                            )
                        )
            except (OSError, json.JSONDecodeError):
                continue

    return msgs


claude = Agent(
    name="claude",
    chats_dir=Path.home() / ".claude" / "projects",
    chats_loader=_load_claude_chats,
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
    chats_loader=_load_codex_chats,
    task_args=lambda cmd, task: [cmd, "exec", task, "--skip-git-repo-check"],
)

gemini = Agent(
    name="gemini",
    chats_dir=Path.home() / ".gemini" / "tmp",
    chats_loader=_load_gemini_chats,
    task_args=lambda cmd, task: [cmd, "-p", task],
)

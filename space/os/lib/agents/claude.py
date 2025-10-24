import json
import subprocess
from pathlib import Path

from space.os import config
from space.os.lib.models import Message


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


def sessions() -> list[Message]:
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return []

    msgs = []
    for project_dir in projects_dir.iterdir():
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
                            Message(
                                role=role,
                                text=text,
                                timestamp=raw.get("timestamp"),
                                session_id=str(jsonl_file.stem),
                            )
                        )
            except (OSError, json.JSONDecodeError):
                continue

    return [m for m in msgs if m.is_valid()]


def spawn(identity: str, task: str | None = None) -> str:
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
        allowed_tools = "Bash Edit Read Glob Grep LS Write WebFetch"
        result = subprocess.run(
            [command, "-p", task, "--allowedTools", allowed_tools],
            capture_output=True,
            text=True,
        )
        return result.stdout
    from space.os.spawn import spawn as spawn_launcher

    role = identity.split("-")[0] if "-" in identity else identity
    spawn_launcher.launch_agent(
        role=role,
        identity=identity,
        base_identity=base_identity,
        model=model,
    )
    return ""

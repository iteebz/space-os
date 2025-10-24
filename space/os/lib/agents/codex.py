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
    sessions_dir = Path.home() / ".codex" / "sessions"
    if not sessions_dir.exists():
        return []

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
                        Message(
                            role=role,
                            text=text,
                            timestamp=raw.get("timestamp"),
                            session_id=str(jsonl_file.stem),
                            model=model_cache[jsonl_file],
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
        result = subprocess.run(
            [command, "exec", task, "--skip-git-repo-check"],
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

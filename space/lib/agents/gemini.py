import json
import subprocess
from pathlib import Path

from space import config
from space.lib.models import Message


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
    gemini_dir = Path.home() / ".gemini" / "tmp"
    if not gemini_dir.exists():
        return []

    msgs = []
    for json_file in gemini_dir.rglob("*.json"):
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
                        Message(
                            role=role,
                            text=text,
                            timestamp=raw.get("timestamp"),
                            session_id=session_id,
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
            [command, "-p", task],
            capture_output=True,
            text=True,
        )
        return result.stdout
    from space.spawn import spawn as spawn_launcher

    role = identity.split("-")[0] if "-" in identity else identity
    spawn_launcher.launch_agent(
        role=role,
        identity=identity,
        base_identity=base_identity,
        model=model,
    )
    return ""

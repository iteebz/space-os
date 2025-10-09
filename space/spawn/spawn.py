import hashlib
import os
import shlex
import shutil
import sys
from pathlib import Path

import yaml

from . import config, registry


def load_config() -> dict:
    with open(config.CONFIG_FILE) as f:
        return yaml.safe_load(f)


def hash_content(content: str) -> str:
    """Hash final injected identity (constitution + self-description).

    Constitution versioning via git commits. This hashes what actually runs.
    """
    return hashlib.sha256(content.encode()).hexdigest()


def get_constitution_path(role: str) -> Path:
    cfg = load_config()
    if role not in cfg["roles"]:
        raise ValueError(f"Unknown role: {role}")
    return _resolve_constitution_path(cfg["roles"][role]["constitution"])


def _resolve_constitution_path(value: str) -> Path:
    """Resolve a constitution path from config entry."""

    expanded = Path(value).expanduser()

    if expanded.is_absolute():
        return expanded

    parts = list(expanded.parts)
    if parts and parts[0] == "constitutions":
        parts = parts[1:]

    relative = Path(*parts) if parts else Path(expanded.name)
    return (config.CONSTITUTIONS_DIR / relative).resolve()


def get_base_identity(role: str) -> str:
    cfg = load_config()
    if role not in cfg["roles"]:
        raise ValueError(f"Unknown role: {role}")
    return cfg["roles"][role]["base_identity"]


def inject_identity(
    base_constitution_content: str, sender_id: str, model: str | None = None
) -> str:
    registry.init_db()
    self_desc = registry.get_self_description(sender_id)

    header_parts = [f"You are now {sender_id}"]
    if model:
        header_parts.append(f"powered by {model}")
    header = " ".join(header_parts) + "."

    if self_desc:
        return f"{header}\nSelf: {self_desc}\n\n{base_constitution_content}"
    return f"{header}\n{base_constitution_content}"


def auto_register_if_needed(role: str, model: str | None = None) -> str:
    """Auto-register role with base_identity to 'general' topic if not exists.

    Returns sender_id.
    """
    sender_id = get_base_identity(role)
    existing = registry.get_registration(role, sender_id, "general")
    if not existing:
        register_agent(role, sender_id, "general", model)
    return sender_id


def register_agent(role: str, sender_id: str, topic: str, model: str | None = None) -> dict:
    const_path = get_constitution_path(role)
    base_content = const_path.read_text()
    full_identity = inject_identity(base_content, sender_id, model)
    const_hash = hash_content(full_identity)
    registry.save_constitution(const_hash, full_identity)
    reg_id = registry.register(role, sender_id, topic, const_hash, model)

    return {
        "id": reg_id,
        "role": role,
        "sender_id": sender_id,
        "topic": topic,
        "constitution_hash": const_hash[:8],
        "model": model,
    }


def launch_agent(
    role: str,
    sender_id: str | None = None,  # This is the agent_name
    base_identity: str | None = None,  # This is the 'agent' argument in the old signature
    extra_args: list[str] | None = None,
    model: str | None = None,
):
    """Launch an agent with a specific role.

    extra_args: Additional CLI arguments forwarded to the underlying agent
    command. These are sourced from inline spawn invocations like
    `spawn sentinel --resume` where `--resume` configures the agent itself
    rather than selecting a different identity.

    model: Model override (e.g., 'claude-4.5-sonnet', 'gpt-5-codex')
    """
    import subprocess

    import click

    cfg = load_config()

    # Use sender_id if provided, otherwise infer from role's base_identity
    actual_sender_id = sender_id or get_base_identity(role)
    # Use base_identity if provided, otherwise infer from role's base_identity
    actual_base_identity = base_identity or get_base_identity(role)
    agent_cfg = cfg.get("agents", {}).get(actual_base_identity)

    if not agent_cfg or "command" not in agent_cfg:
        raise ValueError(f"Agent '{actual_base_identity}' is not configured for launching.")

    const_path = get_constitution_path(role)
    base_content = const_path.read_text()
    full_identity = inject_identity(base_content, actual_sender_id, model)
    const_hash = hash_content(full_identity)
    registry.save_constitution(const_hash, full_identity)

    _sync_identity_targets(agent_cfg, full_identity)

    command_tokens = _parse_command(agent_cfg["command"])
    env = _build_launch_env()
    workspace_root = config.workspace_root()
    env["PWD"] = str(workspace_root)
    command_tokens[0] = _resolve_executable(command_tokens[0], env)

    constitution_args = _constitution_args_from_content(agent_cfg, full_identity)
    passthrough = extra_args or []
    model_args = ["--model", model] if model else []
    full_command = command_tokens + model_args + passthrough + constitution_args

    model_suffix = f" (model: {model})" if model else ""
    click.echo(
        f"Spawning {actual_sender_id} (base: {actual_base_identity}) as a {role}{model_suffix}..."
    )
    click.echo(f"Executing: {' '.join(full_command)}")
    subprocess.run(full_command, env=env, check=False, cwd=str(workspace_root))


def _constitution_args_from_content(agent_cfg: dict, constitution_content: str) -> list[str]:
    """Return the arguments that convey the constitution to the agent."""

    enabled = agent_cfg.get("append_constitution", True)
    if not enabled:
        return []

    value = agent_cfg.get("constitution_arg", "--constitution")
    if isinstance(value, list):
        return [*value, constitution_content]
    if isinstance(value, str):
        return [value, constitution_content]

    raise ValueError("constitution_arg must be a string or list of strings")


def _sync_identity_targets(agent_cfg: dict, content: str) -> None:
    """Materialise the constitution into configured identity targets."""

    targets = agent_cfg.get("identity_targets")
    if not targets:
        return

    for target in _normalise_identity_targets(targets):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def _normalise_identity_targets(targets: str | list[str]) -> list[Path]:
    if isinstance(targets, str):
        targets_list = [targets]
    elif isinstance(targets, list):
        targets_list = targets
    else:
        raise ValueError("identity_targets must be a string or list of strings")

    materialised: list[Path] = []
    for raw in targets_list:
        path = Path(raw).expanduser()
        materialised.append(path)
    return materialised


def _parse_command(command: str | list[str]) -> list[str]:
    """Return the command tokens for launching an agent."""

    if isinstance(command, list):
        if not command:
            raise ValueError("Command list cannot be empty")
        return list(command)

    tokens = shlex.split(command)
    if not tokens:
        raise ValueError("Command cannot be empty")
    return tokens


def _build_launch_env() -> dict[str, str]:
    """Return environment variables for launching outside the poetry venv."""

    env = os.environ.copy()
    venv_paths = _virtualenv_bin_paths(env)
    env.pop("VIRTUAL_ENV", None)
    original_path = env.get("PATH", "")
    filtered_parts: list[str] = []
    for part in original_path.split(os.pathsep):
        if part and part not in venv_paths:
            filtered_parts.append(part)

    # Preserve order while removing duplicates
    seen: set[str] = set()
    deduped_parts: list[str] = []
    for part in filtered_parts:
        if part not in seen:
            seen.add(part)
            deduped_parts.append(part)

    env["PATH"] = os.pathsep.join(deduped_parts)
    return env


def _virtualenv_bin_paths(env: dict[str, str]) -> set[str]:
    """Collect bin directories for active virtual environments."""

    paths: set[str] = set()

    venv_root = env.get("VIRTUAL_ENV")
    if venv_root:
        paths.add(str(Path(venv_root) / "bin"))

    prefix = Path(sys.prefix)
    base_prefix = Path(getattr(sys, "base_prefix", sys.prefix))
    if prefix != base_prefix:
        paths.add(str(prefix / "bin"))

    exec_prefix = Path(sys.exec_prefix)
    base_exec_prefix = Path(getattr(sys, "base_exec_prefix", sys.exec_prefix))
    if exec_prefix != base_exec_prefix:
        paths.add(str(exec_prefix / "bin"))

    return paths


def _resolve_executable(executable: str, env: dict[str, str]) -> str:
    """Resolve the executable path using the sanitized PATH."""

    if os.path.isabs(executable):
        return executable

    search_path = env.get("PATH") or None
    resolved = shutil.which(executable, path=search_path)
    if not resolved:
        raise ValueError(f"Executable '{executable}' not found on PATH")
    return resolved

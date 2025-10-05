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
    return hashlib.sha256(content.encode()).hexdigest()


def get_constitution_path(role: str) -> Path:
    cfg = load_config()
    if role not in cfg["roles"]:
        raise ValueError(f"Unknown role: {role}")

    role_cfg = cfg["roles"][role]
    const_path = _resolve_constitution_path(role_cfg["constitution"])

    if not const_path.exists():
        raise FileNotFoundError(f"Constitution not found: {const_path}")

    return const_path


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


def write_bridge_identity(sender_identity: str, content: str):
    bridge_identities_dir = config.bridge_identities_dir()
    bridge_identities_dir.mkdir(parents=True, exist_ok=True)
    identity_file = bridge_identities_dir / f"{sender_identity}.md"
    identity_file.write_text(content)


def register_agent(role: str, sender_id: str, topic: str) -> dict:
    """Register agent with spawn registry and materialize identity for bridge."""
    const_path = get_constitution_path(role)
    constitution = const_path.read_text()
    
    registry.init_db()
    self_desc = registry.get_self_description(sender_id)
    
    if self_desc:
        identity_header = f"You are now {sender_id}.\nSelf: {self_desc}\n\n"
        full_identity = identity_header + constitution
    else:
        full_identity = constitution
    
    const_hash = hash_content(full_identity)
    write_bridge_identity(sender_id, full_identity)
    reg_id = registry.register(role, sender_id, topic, const_hash)

    return {
        "id": reg_id,
        "role": role,
        "sender_id": sender_id,
        "topic": topic,
        "constitution_hash": const_hash[:8],
        "constitution_path": str(const_path),
    }


def launch_agent(role: str, agent: str | None = None, extra_args: list[str] | None = None):
    """Launch an agent with a specific role.

    extra_args: Additional CLI arguments forwarded to the underlying agent
    command. These are sourced from inline spawn invocations like
    `spawn sentinel --resume` where `--resume` configures the agent itself
    rather than selecting a different identity.
    """
    import subprocess

    import click

    cfg = load_config()
    agent_name = agent or get_base_identity(role)

    agent_cfg = cfg.get("agents", {}).get(agent_name)
    if not agent_cfg or "command" not in agent_cfg:
        raise ValueError(f"Agent '{agent_name}' is not configured for launching.")

    const_path = get_constitution_path(role)
    const_content = const_path.read_text()
    write_bridge_identity(agent_name, const_content)
    identity_dir = config.bridge_identities_dir()
    identity_file = identity_dir / f"{agent_name}.md"

    _sync_identity_targets(agent_cfg, const_content)

    command_tokens = _parse_command(agent_cfg["command"])
    env = _build_launch_env()
    workspace_root = config.workspace_root()
    env["PWD"] = str(workspace_root)
    command_tokens[0] = _resolve_executable(command_tokens[0], env)

    constitution_args = _constitution_args(agent_cfg, identity_file)
    passthrough = extra_args or []
    full_command = command_tokens + passthrough + constitution_args

    click.echo(f"Spawning {agent_name} as a {role}...")
    click.echo(f"Executing: {' '.join(full_command)}")
    subprocess.run(full_command, env=env, check=False, cwd=str(workspace_root))


def _constitution_args(agent_cfg: dict, identity_file: Path) -> list[str]:
    """Return the arguments that convey the constitution to the agent."""

    enabled = agent_cfg.get("append_constitution", True)
    if not enabled:
        return []

    value = agent_cfg.get("constitution_arg", "--constitution")
    if isinstance(value, list):
        return [*value, str(identity_file)]
    if isinstance(value, str):
        return [value, str(identity_file)]

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

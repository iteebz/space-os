import hashlib
import os
import shlex
import shutil
import sys
from pathlib import Path

import yaml

from . import config, registry
from ..lib import fs, hashing
from ..lib.storage import constitutions


def load_config() -> dict:
    with open(config.CONFIG_FILE) as f:
        return yaml.safe_load(f)


def get_constitution_path(role: str) -> Path:
    cfg = load_config()
    if role not in cfg["roles"]:
        raise ValueError(f"Unknown role: {role}")

    role_cfg = cfg["roles"][role]
    const_path = fs.constitutions_dir() / role_cfg["constitution"]

    if not const_path.exists():
        raise FileNotFoundError(f"Constitution not found: {const_path}")

    return const_path


def get_base_identity(role: str) -> str:
    cfg = load_config()
    if role not in cfg["roles"]:
        raise ValueError(f"Unknown role: {role}")
    return cfg["roles"][role]["base_identity"]


def inject_identity(constitution: str, sender_id: str, self_description: str | None = None) -> str:
    registry.init_db()
    if self_description is None:
        self_description = registry.get_self_description(sender_id)
    if not self_description:
        return constitution
    return f"You are now {sender_id}.\nSelf: {self_description}\n\n{constitution}"


def register_agent(role: str, sender_id: str, topic: str, model: str | None = None, provider: str | None = None) -> dict:
    const_path = get_constitution_path(role)
    full_identity = inject_identity(const_path.read_text(), sender_id)
    const_hash = hashing.sha256(full_identity) # Use full hash for internal consistency
    constitutions.track("constitution", full_identity) # Autoregister the constitution
    reg_id = registry.register(
        agent_id=sender_id, role=role, channels=[topic], constitution_hash=const_hash, constitution_content=full_identity, model=model, provider=provider
    )

    return {
        "id": reg_id,
        "role": role,
        "sender_id": sender_id,
        "topic": topic,
        "constitution_hash": hashing.sha256(full_identity, 8),
        "constitution_path": str(const_path),
        "model": model,
        "provider": provider,
    }


def launch_agent(
    role: str,
    agent: str | None = None,
    extra_args: list[str] | None = None,
    model: str | None = None,
    provider: str | None = None,
    self_description: str | None = None,
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
    agent_name = agent or get_base_identity(role)

    agent_cfg = cfg.get("agents", {}).get(agent_name)
    if not agent_cfg or "command" not in agent_cfg:
        raise ValueError(f"Agent '{agent_name}' is not configured for launching.")

    reg = registry.fetch_by_sender(agent_name)
    if not reg:
        raise ValueError(f"No entry found for sender '{agent_name}'")

    constitution_content = reg.constitution_content
    constitution_hash = reg.constitution_hash

    _sync_identity_targets(agent_cfg, constitution_content)

    command_tokens = _parse_command(agent_cfg["command"])
    env = _build_launch_env()
    workspace_root = fs.root()
    env["PWD"] = str(workspace_root)
    if model:
        env["AGENT_MODEL"] = model
    if provider:
        env["AGENT_PROVIDER"] = provider
    if self_description:
        env["AGENT_SELF_DESCRIPTION"] = self_description
    if constitution_hash:
        env["AGENT_CONSTITUTION_HASH"] = constitution_hash
    command_tokens[0] = _resolve_executable(command_tokens[0], env)

    constitution_args = _constitution_args(agent_cfg, constitution_content)
    passthrough = extra_args or []
    full_command = command_tokens + passthrough + constitution_args

    model_suffix = f" (model: {model})" if model else ""
    provider_suffix = f" (provider: {provider})" if provider else ""
    self_description_suffix = f" (self_description: {self_description})" if self_description else ""
    click.echo(f"Spawning {agent_name} as a {role}{model_suffix}{provider_suffix}{self_description_suffix}...")
    click.echo(f"Executing: {' '.join(full_command)}")
    subprocess.run(full_command, env=env, check=False, cwd=str(workspace_root))


def _constitution_args(agent_cfg: dict, full_identity_content: str) -> list[str]:
    """Return the arguments that convey the constitution to the agent."""
    import tempfile

    enabled = agent_cfg.get("append_constitution", True)
    if not enabled:
        return []

    # Create a temporary file for the constitution content
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(full_identity_content)
        temp_file_path = Path(temp_file.name)

    value = agent_cfg.get("constitution_arg", "--constitution")
    if isinstance(value, list):
        return [*value, str(temp_file_path)]
    if isinstance(value, str):
        return [value, str(temp_file_path)]

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
    base_exec_prefix = Path(getattr(sys, "base_prefix", sys.exec_prefix))
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

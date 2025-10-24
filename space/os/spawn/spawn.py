import hashlib
import os
import shlex
import shutil
import sys
from pathlib import Path

from .. import config
from ..lib import paths
from . import registry


def hash_content(content: str) -> str:
    """Hash final injected identity (constitution + self-description).

    Constitution versioning via git commits. This hashes what actually runs.
    """
    return hashlib.sha256(content.encode()).hexdigest()


def get_constitution_path(role: str) -> Path:
    config.init_config()
    cfg = config.load_config()
    constitution_filename = cfg["roles"][role]["constitution"]

    prompt_path = paths.canon_path() / "prompts" / constitution_filename
    if prompt_path.exists():
        return prompt_path

    return paths.constitution(constitution_filename)


def get_base_identity(role: str) -> str:
    config.init_config()
    cfg = config.load_config()
    if role not in cfg["roles"]:
        raise ValueError(f"Unknown role: {role}")
    return cfg["roles"][role]["base_identity"]


def resolve_model_alias(alias: str) -> str:
    """Resolve model alias to full model name."""
    config.init_config()
    cfg = config.load_config()
    aliases = cfg.get("model_aliases", {})
    return aliases.get(alias, alias)


def inject_identity(
    base_constitution_content: str, role: str, identity: str, model: str | None = None
) -> str:
    """Injects identity (self-description + model) into the constitution.

    Assembly order: header → self → constitution → footer.
    """
    parts = []

    parts.append(f"# {role.upper()} CONSTITUTION")
    parts.append("")

    if model:
        parts.append(f"Self: You are {identity}. Your model is {model}.")
    else:
        parts.append(f"Self: You are {identity}.")

    parts.append("")
    parts.append(base_constitution_content)

    parts.append("")
    parts.append("run `space` for orientation (already in PATH).")
    parts.append(f"run: `memory --as {identity}` to access memories.")

    return "\n".join(parts)


def _run_wake_sequence(identity: str) -> str | None:
    """Run wake and memory load sequence for identity. Returns wake output for agent context."""
    import io
    from contextlib import redirect_stdout

    from ..commands import wake
    from . import registry

    registry.init_db()

    output = io.StringIO()
    with redirect_stdout(output):
        wake.wake(identity=identity, quiet=False)

    return output.getvalue() if output.getvalue() else None


def launch_agent(
    role: str,
    identity: str | None = None,
    base_identity: str | None = None,  # CLI client (claude, gemini, codex)
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

    config.init_config()
    cfg = config.load_config()

    # Use identity if provided, otherwise infer from role's base_identity
    actual_identity = identity or get_base_identity(role)
    # Use base_identity if provided, otherwise infer from role's base_identity
    actual_base_identity = base_identity or get_base_identity(role)
    agent_cfg = cfg.get("agents", {}).get(actual_base_identity)

    if not agent_cfg or "command" not in agent_cfg:
        raise ValueError(f"Agent '{actual_base_identity}' is not configured for launching.")

    actual_model = model or agent_cfg.get("model")

    const_path = get_constitution_path(role)
    base_content = const_path.read_text()
    full_identity = inject_identity(base_content, role, actual_identity, actual_model)
    const_hash = hash_content(full_identity)
    registry.save_constitution(const_hash, full_identity)

    _write_identity_file(actual_base_identity, actual_identity, full_identity)

    command_tokens = _parse_command(agent_cfg["command"])
    env = _build_launch_env()
    workspace_root = paths.space_root()
    env["PWD"] = str(workspace_root)
    command_tokens[0] = _resolve_executable(command_tokens[0], env)

    passthrough = extra_args or []
    model_args = ["--model", actual_model] if actual_model else []

    role_cfg = cfg["roles"][role]
    wake_output = None
    if role_cfg.get("wake_on_spawn"):
        click.echo(f"Waking {actual_identity}...\n")
        wake_output = _run_wake_sequence(actual_identity)

    if wake_output:
        if "gemini" in command_tokens[0]:
            passthrough = ["-i", wake_output] + passthrough
        elif "codex" in command_tokens[0]:
            passthrough = [wake_output] + passthrough

    full_command = command_tokens + model_args + passthrough

    const_filename = cfg["roles"][role]["constitution"]
    model_suffix = f" --model {actual_model}" if actual_model else ""
    click.echo(f"Spawning {role} with {const_filename}{model_suffix}")
    click.echo(f"Executing: {' '.join(full_command)}")

    if wake_output and "claude" in command_tokens[0]:
        proc = subprocess.Popen(
            full_command, env=env, cwd=str(workspace_root), stdin=subprocess.PIPE, text=True
        )
        proc.stdin.write(wake_output + "\n")
        proc.stdin.close()
        proc.wait()
    else:
        subprocess.run(full_command, env=env, check=False, cwd=str(workspace_root))


def _write_identity_file(base_identity: str, identity: str, content: str) -> None:
    """Write constitution to the base identity's file (CLAUDE.md, GEMINI.md, etc)."""
    filename_map = {
        "sonnet": "CLAUDE.md",
        "haiku": "CLAUDE.md",
        "gemini": "GEMINI.md",
        "codex": "AGENTS.md",
    }
    filename = filename_map.get(base_identity)
    if not filename:
        raise ValueError(f"Unknown base_identity: {base_identity}")

    target = paths.space_root() / filename
    target.write_text(content)


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
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    env.pop("CLAUDECODE", None)
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

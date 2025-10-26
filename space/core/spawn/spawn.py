import os
import shlex
import shutil
import sys
from pathlib import Path

from space import config
from space.lib import paths


def get_provider_command(provider: str) -> str:
    """Map provider name to CLI command."""
    provider_map = {
        "claude": "claude",
        "gemini": "gemini",
        "codex": "codex",
    }
    cmd = provider_map.get(provider)
    if not cmd:
        raise ValueError(f"Unknown provider: {provider}")
    return cmd


def resolve_model_alias(alias: str) -> str:
    """Resolve model alias to full model name."""
    config.init_config()
    cfg = config.load_config()
    aliases = cfg.get("model_aliases", {})
    return aliases.get(alias, alias)


def build_identity_prompt(role: str, model: str | None = None) -> str:
    """Build identity and space instructions for first prompt injection."""
    parts = [f"You are {role}."]
    if model:
        parts[0] += f" Your model is {model}."
    parts.append("")
    parts.append("space commands:")
    parts.append("  run `space` for orientation (already in PATH)")
    parts.append(f"  run `memory --as {role}` to access memories")
    return "\n".join(parts)


def _run_wake_sequence(role: str) -> str | None:
    """Run wake and memory load sequence for role. Returns wake output for agent context."""
    import io
    from contextlib import redirect_stdout

    from ...commands import wake

    output = io.StringIO()
    with redirect_stdout(output):
        wake.wake(role=role, quiet=False)

    return output.getvalue() if output.getvalue() else None


def launch_agent(
    identity: str,
    extra_args: list[str] | None = None,
):
    """Launch an agent by identity from registry.

    Writes pure constitution to agent home dir, injects identity via stdin.

    extra_args: Additional CLI arguments forwarded to the underlying agent
    command. These are sourced from inline spawn invocations like
    `spawn sentinel --resume` where `--resume` configures the agent itself
    rather than selecting a different role.
    """
    import subprocess

    import click

    from space.core.spawn import api

    agent = api.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found in registry")

    const_path = paths.constitution(agent.constitution)
    constitution_text = const_path.read_text()

    provider_cmd = get_provider_command(agent.provider)
    _write_role_file(agent.provider, constitution_text)

    command_tokens = _parse_command(provider_cmd)
    env = _build_launch_env()
    workspace_root = paths.space_root()
    env["PWD"] = str(workspace_root)
    command_tokens[0] = _resolve_executable(command_tokens[0], env)

    passthrough = extra_args or []
    model_args = ["--model", agent.model]

    wake_output = None
    click.echo(f"Waking {identity}...\n")
    wake_output = _run_wake_sequence(identity)

    identity_prompt = build_identity_prompt(identity, agent.model)
    stdin_content = identity_prompt
    if wake_output:
        stdin_content = identity_prompt + "\n\n" + wake_output

    full_command = command_tokens + model_args + passthrough

    click.echo(f"Spawning {identity} with {agent.constitution} --model {agent.model}")
    click.echo(f"Executing: {' '.join(full_command)}")

    proc = subprocess.Popen(
        full_command, env=env, cwd=str(workspace_root), stdin=subprocess.PIPE, text=True
    )
    proc.stdin.write(stdin_content + "\n")
    proc.stdin.close()
    proc.wait()


def _write_role_file(provider: str, constitution: str) -> None:
    """Write pure constitution to agent home dir file."""
    filename_map = {
        "claude": "CLAUDE.md",
        "gemini": "GEMINI.md",
        "codex": "AGENTS.md",
    }
    agent_dir_map = {
        "claude": ".claude",
        "gemini": ".gemini",
        "codex": ".codex",
    }
    filename = filename_map.get(provider)
    agent_dir = agent_dir_map.get(provider)
    if not filename or not agent_dir:
        raise ValueError(f"Unknown provider: {provider}")

    target = Path.home() / agent_dir / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(constitution)


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

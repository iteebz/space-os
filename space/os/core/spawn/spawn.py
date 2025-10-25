import os
import shlex
import shutil
import sys
from pathlib import Path

from space.os import config
from space.os.lib import paths


def get_base_agent(role: str) -> str:
    config.init_config()
    cfg = config.load_config()
    if role not in cfg["roles"]:
        raise ValueError(f"Unknown role: {role}")
    return cfg["roles"][role]["base_agent"]


def resolve_model_alias(alias: str) -> str:
    """Resolve model alias to full model name."""
    config.init_config()
    cfg = config.load_config()
    aliases = cfg.get("model_aliases", {})
    return aliases.get(alias, alias)


def inject_role(
    base_constitution_content: str, constitution: str, role: str, model: str | None = None
) -> str:
    """Injects role (self-description + model) into the constitution.

    Assembly order: header → self → constitution → footer.
    """
    parts = []

    parts.append(f"# {constitution.upper()} CONSTITUTION")
    parts.append("")

    if model:
        parts.append(f"Self: You are {role}. Your model is {model}.")
    else:
        parts.append(f"Self: You are {role}.")

    parts.append("")
    parts.append(base_constitution_content)

    parts.append("")
    parts.append("run `space` for orientation (already in PATH).")
    parts.append(f"run: `memory --as {role}` to access memories.")

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
    constitution: str,
    role: str | None = None,
    base_agent: str | None = None,  # CLI client (claude, gemini, codex)
    extra_args: list[str] | None = None,
    model: str | None = None,
):
    """Launch an agent with a specific constitutional role.

    extra_args: Additional CLI arguments forwarded to the underlying agent
    command. These are sourced from inline spawn invocations like
    `spawn sentinel --resume` where `--resume` configures the agent itself
    rather than selecting a different role.

    model: Model override (e.g., 'claude-4.5-sonnet', 'gpt-5-codex')
    """
    import subprocess

    import click

    config.init_config()
    cfg = config.load_config()

    # Use role if provided, otherwise infer from constitution's base_agent
    actual_role = role or get_base_agent(constitution)
    # Use base_agent if provided, otherwise infer from constitution's base_agent
    actual_base_agent = base_agent or get_base_agent(constitution)
    agent_cfg = cfg.get("agents", {}).get(actual_base_agent)

    if not agent_cfg or "command" not in agent_cfg:
        raise ValueError(f"Agent '{actual_base_agent}' is not configured for launching.")

    actual_model = model or agent_cfg.get("model")

    role_cfg = cfg["roles"][constitution]
    const_filename = role_cfg["constitution"]
    const_path = paths.constitution(const_filename)
    base_content = const_path.read_text()
    full_role = inject_role(base_content, constitution, actual_role, actual_model)

    _write_role_file(actual_base_agent, actual_role, full_role)

    command_tokens = _parse_command(agent_cfg["command"])
    env = _build_launch_env()
    workspace_root = paths.space_root()
    env["PWD"] = str(workspace_root)
    command_tokens[0] = _resolve_executable(command_tokens[0], env)

    passthrough = extra_args or []
    model_args = ["--model", actual_model] if actual_model else []

    role_cfg = cfg["roles"][constitution]
    wake_output = None
    if role_cfg.get("wake_on_spawn"):
        click.echo(f"Waking {actual_role}...\n")
        wake_output = _run_wake_sequence(actual_role)

    if wake_output:
        if "gemini" in command_tokens[0]:
            passthrough = ["-i", wake_output] + passthrough
        elif "codex" in command_tokens[0]:
            passthrough = [wake_output] + passthrough

    full_command = command_tokens + model_args + passthrough

    const_filename = cfg["roles"][constitution]["constitution"]
    model_suffix = f" --model {actual_model}" if actual_model else ""
    click.echo(f"Spawning {constitution} with {const_filename}{model_suffix}")
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


def _write_role_file(base_agent: str, role: str, content: str) -> None:
    """Write constitution to the base agent's file (CLAUDE.md, GEMINI.md, etc)."""
    filename_map = {
        "sonnet": "CLAUDE.md",
        "haiku": "CLAUDE.md",
        "gemini": "GEMINI.md",
        "codex": "AGENTS.md",
    }
    filename = filename_map.get(base_agent)
    if not filename:
        raise ValueError(f"Unknown base_agent: {base_agent}")

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

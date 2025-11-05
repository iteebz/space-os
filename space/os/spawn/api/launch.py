"""Agent launching: provider execution and lifecycle management."""

import json
import logging
import os
import shlex
import shutil
import subprocess

import typer

from space.lib import paths
from space.lib.providers import Claude, Codex, Gemini
from space.os.sessions.api import resolve_session_id

from . import agents, spawns
from .constitute import constitute
from .environment import build_launch_env
from .prompt import build_spawn_context

logger = logging.getLogger(__name__)


def spawn_interactive(
    identity: str,
    extra_args: list[str] | None = None,
    resume: str | None = None,
):
    """Spawn an agent by identity from registry (interactive mode).

    Looks up agent, writes constitution to provider home dir,
    injects unified context via stdin, and executes the provider CLI.

    Args:
        identity: Agent identity from registry
        extra_args: Additional CLI arguments forwarded to provider.
        resume: Session/spawn ID to resume, or None to continue last.
    """
    agent = agents.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found in registry")

    constitution_hash = agents.compute_constitution_hash(agent.constitution)

    provider_cmd = _get_provider_command(agent.provider)
    command_tokens = _parse_command(provider_cmd)
    env = build_launch_env()
    env["PWD"] = str(paths.space_root())
    command_tokens[0] = _resolve_executable(command_tokens[0], env)

    passthrough = extra_args or []
    model_args = ["--model", agent.model]

    typer.echo(f"Spawning {identity}...\n")
    spawn = spawns.create_spawn(
        agent_id=agent.agent_id,
        is_task=bool(passthrough),
        constitution_hash=constitution_hash,
    )

    constitute(spawn, agent)

    provider_class = {"claude": Claude, "gemini": Gemini, "codex": Codex}.get(agent.provider)
    if provider_class:
        if agent.provider == "gemini":
            launch_args = provider_class.launch_args(has_prompt=bool(passthrough))
        elif agent.provider == "claude":
            launch_args = provider_class.launch_args(is_task=bool(passthrough))
        else:
            launch_args = provider_class.launch_args()
    else:
        launch_args = []

    add_dir_args = ["--add-dir", str(paths.space_root())]

    session_id = resolve_session_id(agent.agent_id, resume)
    resume_args = _build_resume_args(agent.provider, session_id, resume is None and session_id)

    if passthrough:
        context = build_spawn_context(identity, task=passthrough[0] if passthrough else None)
        full_command = (
            command_tokens + add_dir_args + [context] + model_args + launch_args + resume_args
        )
        display_command = (
            command_tokens + add_dir_args + ['"<context>"'] + model_args + launch_args + resume_args
        )
    else:
        context = build_spawn_context(identity)
        full_command = command_tokens + add_dir_args + model_args + launch_args + resume_args
        display_command = full_command

    typer.echo(f"Executing: {' '.join(display_command)}")
    typer.echo("")

    if passthrough:
        spawn_dir = paths.identity_dir(agent.identity)
        popen_kwargs = {
            "env": env,
            "cwd": str(spawn_dir),
            "stdin": subprocess.PIPE,
        }
        proc = subprocess.Popen(full_command, **popen_kwargs)
        try:
            proc.communicate()
        finally:
            spawns.end_spawn(spawn.id)
    else:
        import sys

        popen_kwargs = {
            "env": env,
            "cwd": str(paths.space_root()),
            "stdin": subprocess.PIPE,
            "stdout": sys.stdout,
            "stderr": sys.stderr,
        }
        proc = subprocess.Popen(full_command, **popen_kwargs)
        try:
            proc.stdin.write(context.encode() + b"\n")
            proc.stdin.close()
            proc.wait()
        finally:
            spawns.end_spawn(spawn.id)


def spawn_task(
    identity: str,
    task: str,
    channel_id: str,
    resume: str | None = None,
):
    """Spawn an agent as a task-based execution (non-interactive).

    Args:
        identity: Agent identity from registry
        task: Task/prompt to execute
        channel_id: Channel ID (for bridge context, optional)
        resume: Session/spawn ID to resume, or None to continue last

    Returns:
        Spawn object
    """
    from space.os.bridge.api import channels

    agent = agents.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found in registry")

    constitution_hash = agents.compute_constitution_hash(agent.constitution)

    spawn = spawns.create_spawn(
        agent_id=agent.agent_id,
        is_task=True,
        channel_id=channel_id,
        constitution_hash=constitution_hash,
    )
    spawns.update_status(spawn.id, "running")

    constitute(spawn, agent)

    channel = channels.get_channel(channel_id) if channel_id else None
    channel_name = channel.name if channel else None

    session_id = resolve_session_id(agent.agent_id, resume)

    try:
        if agent.provider == "claude":
            _spawn_task_claude(
                agent, task, spawn, channel_name, session_id, resume is None and session_id
            )
        elif agent.provider == "gemini":
            _spawn_task_gemini(agent, task, spawn, channel_name)
        elif agent.provider == "codex":
            _spawn_task_codex(
                agent, task, spawn, channel_name, session_id, resume is None and session_id
            )
        else:
            raise ValueError(f"Unknown provider: {agent.provider}")

        spawns.update_status(spawn.id, "completed")
        return spawn
    except Exception as e:
        logger.error(f"Headless spawn failed for {identity}: {e}", exc_info=True)
        spawns.update_status(spawn.id, "failed")
        raise


def _spawn_task_claude(
    agent,
    task: str,
    spawn,
    channel_name: str | None,
    session_id: str | None = None,
    is_continue: bool = False,
) -> None:
    """Execute task-based Claude Code spawn with session linking.

    If spawned from a channel (@mention), agent should post results to that channel.
    """
    import sys

    from space.os.sessions.api import linker

    launch_args = Claude.task_launch_args()

    context = build_spawn_context(agent.identity, task=task, channel=channel_name, is_task=True)
    add_dir_args = ["--add-dir", str(paths.space_root())]
    resume_args = _build_resume_args("claude", session_id, is_continue)
    cmd = ["claude"] + launch_args + add_dir_args + resume_args

    spawn_dir = paths.identity_dir(agent.identity)
    result = subprocess.run(
        cmd, input=context, capture_output=True, text=True, cwd=str(spawn_dir), timeout=300
    )

    if result.returncode != 0:
        sys.stderr.write(f"Claude spawn failed: {result.stderr}\n")
        raise RuntimeError(f"Claude spawn failed: {result.stderr}")

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Failed to parse Claude output: {result.stdout}\n")
        raise RuntimeError(f"Failed to parse Claude output: {e}") from e

    claude_session_id = output.get("session_id")
    if not claude_session_id:
        raise RuntimeError("No session_id in Claude output")

    linker.link_spawn_to_session(spawn.id, claude_session_id)

    result_text = output.get("result", "")
    if result_text:
        sys.stdout.write(result_text + "\n")


def _spawn_task_gemini(agent, task: str, spawn, channel_name: str | None) -> None:
    """Execute task-based Gemini spawn with session linking.

    If spawned from a channel (@mention), agent should post results to that channel.
    """
    import sys

    from space.os.sessions.api import linker

    launch_args = Gemini.task_launch_args()

    context = build_spawn_context(agent.identity, task=task, channel=channel_name, is_task=True)
    add_dir_args = ["--add-dir", str(paths.space_root())]
    cmd = ["gemini"] + launch_args + add_dir_args

    spawn_dir = paths.identity_dir(agent.identity)
    result = subprocess.run(
        cmd, input=context, capture_output=True, text=True, cwd=str(spawn_dir), timeout=300
    )

    if result.returncode != 0:
        sys.stderr.write(f"Gemini spawn failed: {result.stderr}\n")
        raise RuntimeError(f"Gemini spawn failed: {result.stderr}")

    gemini_session_id = Gemini.session_id(result.stdout)
    if not gemini_session_id:
        raise RuntimeError("No session_id in Gemini output")

    linker.link_spawn_to_session(spawn.id, gemini_session_id)


def _spawn_task_codex(
    agent,
    task: str,
    spawn,
    channel_name: str | None,
    session_id: str | None = None,
    is_continue: bool = False,
) -> None:
    """Execute task-based Codex spawn with session linking.

    If spawned from a channel (@mention), agent should post results to that channel.
    """
    import sys

    from space.os.sessions.api import linker

    launch_args = Codex.task_launch_args()

    context = build_spawn_context(agent.identity, task=task, channel=channel_name, is_task=True)
    add_dir_args = ["--add-dir", str(paths.space_root())]
    resume_args = _build_resume_args("codex", session_id, is_continue)
    cmd = ["codex"] + resume_args + ["exec"] + launch_args + add_dir_args

    spawn_dir = paths.identity_dir(agent.identity)
    result = subprocess.run(
        cmd, input=context, capture_output=True, text=True, cwd=str(spawn_dir), timeout=300
    )

    if result.returncode != 0:
        sys.stderr.write(f"Codex spawn failed: {result.stderr}\n")
        raise RuntimeError(f"Codex spawn failed: {result.stderr}")

    codex_session_id = Codex.session_id(result.stdout)
    if not codex_session_id:
        raise RuntimeError("No session_id in Codex output")

    linker.link_spawn_to_session(spawn.id, codex_session_id)


def _get_provider_command(provider: str) -> str:
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


def _resolve_executable(executable: str, env: dict[str, str]) -> str:
    """Resolve the executable path using the sanitized PATH."""
    if os.path.isabs(executable):
        return executable

    search_path = env.get("PATH") or None
    resolved = shutil.which(executable, path=search_path)
    if not resolved:
        raise ValueError(f"Executable '{executable}' not found on PATH")
    return resolved


def _build_resume_args(provider: str, session_id: str | None, is_continue: bool) -> list[str]:
    """Build provider-specific resume/continue arguments.

    Args:
        provider: Provider name (claude, codex, gemini)
        session_id: Session ID to resume
        is_continue: If True, continue last session (session_id was auto-resolved)

    Returns:
        List of arguments to append to provider command
    """
    if not session_id:
        return []

    if provider == "claude":
        if is_continue:
            return ["-c"]
        return ["-r", session_id]

    if provider == "codex":
        if is_continue:
            return ["resume", "--last"]
        return ["resume", session_id]

    return []

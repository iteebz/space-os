"""Agent launching: provider execution and lifecycle management."""

import hashlib
import json
import logging
import os
import shlex
import shutil
import subprocess

import click

from space.lib import paths
from space.lib.constitution import write_constitution
from space.lib.providers import claude, codex, gemini

from . import agents, spawns
from .environment import build_launch_env
from .prompt import build_spawn_context

logger = logging.getLogger(__name__)


def spawn_interactive(identity: str, extra_args: list[str] | None = None):
    """Spawn an agent by identity from registry (interactive mode).

    Looks up agent, writes constitution to provider home dir,
    injects unified context via stdin, and executes the provider CLI.

    Args:
            identity: Agent identity from registry
            extra_args: Additional CLI arguments forwarded to provider.
                       If empty, spawn in interactive mode without context prompt.
    """
    agent = agents.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found in registry")

    constitution_text = None
    constitution_hash = None
    if agent.constitution:
        const_path = paths.constitution(agent.constitution)
        constitution_text = const_path.read_text()
        constitution_hash = hashlib.sha256(constitution_text.encode()).hexdigest()

    provider_cmd = _get_provider_command(agent.provider)
    if constitution_text:
        _write_constitution(agent.provider, constitution_text)

    command_tokens = _parse_command(provider_cmd)
    env = build_launch_env()
    workspace_root = paths.space_root()
    env["PWD"] = str(workspace_root)
    command_tokens[0] = _resolve_executable(command_tokens[0], env)

    passthrough = extra_args or []
    model_args = ["--model", agent.model]

    click.echo(f"Spawning {identity}...\n")
    spawn = spawns.create_spawn(
        agent_id=agent.agent_id,
        is_task=bool(passthrough),
        constitution_hash=constitution_hash,
    )

    provider_obj = {"claude": claude, "gemini": gemini, "codex": codex}.get(agent.provider)
    if provider_obj:
        if agent.provider == "gemini":
            launch_args = provider_obj.launch_args(has_prompt=bool(passthrough))
        elif agent.provider == "claude":
            launch_args = provider_obj.launch_args(is_task=bool(passthrough))
        else:
            launch_args = provider_obj.launch_args()
    else:
        launch_args = []

    if passthrough:
        context = build_spawn_context(identity, task=passthrough[0] if passthrough else None)
        full_command = command_tokens + [context] + model_args + launch_args
        display_command = command_tokens + ['"<context>"'] + model_args + launch_args
    else:
        context = build_spawn_context(identity)
        full_command = command_tokens + [context] + model_args + launch_args
        display_command = command_tokens + ['"<context>"'] + model_args + launch_args

    click.echo(f"Executing: {' '.join(display_command)}")
    click.echo("")

    if passthrough:
        popen_kwargs = {
            "env": env,
            "cwd": str(workspace_root),
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
            "cwd": str(workspace_root),
            "stdin": sys.stdin,
            "stdout": sys.stdout,
            "stderr": sys.stderr,
        }
        proc = subprocess.Popen(full_command, **popen_kwargs)
        try:
            proc.wait()
        finally:
            spawns.end_spawn(spawn.id)


def spawn_headless(identity: str, task: str, channel_id: str) -> None:
    """Spawn an agent headlessly for bridge mention execution.

    Args:
        identity: Agent identity from registry
        task: Task/prompt to execute
        channel_id: Channel ID (for bridge context)
    """
    from space.os.bridge.api import channels

    agent = agents.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found in registry")

    spawn = spawns.create_spawn(agent_id=agent.agent_id, is_task=True, channel_id=channel_id)
    spawns.update_status(spawn.id, "running")

    channel = channels.get_channel(channel_id) if channel_id else None
    channel_name = channel.name if channel else None

    try:
        if agent.provider == "claude":
            _spawn_headless_claude(agent, task, spawn, channel_name)
        elif agent.provider == "gemini":
            _spawn_headless_gemini(agent, task, spawn, channel_name)
        elif agent.provider == "codex":
            _spawn_headless_codex(agent, task, spawn, channel_name)
        else:
            raise ValueError(f"Unknown provider: {agent.provider}")

        spawns.update_status(spawn.id, "completed")
    except Exception as e:
        logger.error(f"Headless spawn failed for {identity}: {e}", exc_info=True)
        spawns.update_status(spawn.id, "failed")
        raise


def _spawn_headless_claude(agent, task: str, spawn, channel_name: str | None) -> None:
    """Execute headless Claude Code spawn with session linking.

    If spawned from a channel (@mention), agent should post results to that channel.
    """
    from space.os.sessions.api import linker

    provider_obj = claude
    launch_args = provider_obj.launch_args(is_task=True)

    context = build_spawn_context(agent.identity, task=task, channel=channel_name)
    cmd = ["claude", "--print", context, "--output-format", "json"] + launch_args

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(paths.space_root()))

    if result.returncode != 0:
        raise RuntimeError(f"Claude spawn failed: {result.stderr}")

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Claude output: {e}") from e

    claude_session_id = output.get("session_id")
    if not claude_session_id:
        raise RuntimeError("No session_id in Claude output")

    linker.link_spawn_to_session(spawn.id, claude_session_id)


def _spawn_headless_gemini(agent, task: str, spawn, channel_name: str | None) -> None:
    """Execute headless Gemini spawn with session linking.

    Note: Gemini session syncing to ~/.space/sessions/ deferred (handled by sync_provider_sessions).
    If spawned from a channel (@mention), agent should post results to that channel.
    """
    from space.os.sessions.api import linker

    provider_obj = gemini
    launch_args = provider_obj.launch_args(has_prompt=True)

    context = build_spawn_context(agent.identity, task=task, channel=channel_name)
    cmd = ["gemini", context, "--output-format", "stream-json"] + launch_args

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(paths.space_root()))

    if result.returncode != 0:
        raise RuntimeError(f"Gemini spawn failed: {result.stderr}")

    gemini_session_id = provider_obj.headless_session_id(result.stdout)
    if not gemini_session_id:
        raise RuntimeError("No session_id in Gemini output")

    linker.link_spawn_to_session(spawn.id, gemini_session_id)


def _spawn_headless_codex(agent, task: str, spawn, channel_name: str | None) -> None:
    """Execute headless Codex spawn with session linking.

    If spawned from a channel (@mention), agent should post results to that channel.
    """
    from space.os.sessions.api import linker

    provider_obj = codex
    launch_args = provider_obj.launch_args()

    context = build_spawn_context(agent.identity, task=task, channel=channel_name)
    cmd = ["codex", "exec", "--json", context] + launch_args

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(paths.space_root()))

    if result.returncode != 0:
        raise RuntimeError(f"Codex spawn failed: {result.stderr}")

    codex_session_id = provider_obj.headless_session_id(result.stdout)
    if not codex_session_id:
        raise RuntimeError("No session_id in Codex output")

    linker.link_spawn_to_session(spawn.id, codex_session_id)


def spawn_agent(identity: str, extra_args: list[str] | None = None):
    """Backward-compatible wrapper for spawn_interactive."""
    return spawn_interactive(identity, extra_args)


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


def _write_constitution(provider: str, constitution: str) -> None:
    """Write constitution to provider home dir and verify write succeeded."""
    path = write_constitution(provider, constitution)
    with open(path) as f:
        os.fsync(f.fileno())
    if path.read_text() != constitution:
        raise RuntimeError(f"Failed to write constitution to {path}")


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

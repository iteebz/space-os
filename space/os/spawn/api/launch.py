"""Agent launching: provider execution and lifecycle management."""

import json
import os
import shlex
import shutil
import subprocess

import click

from space.lib import paths
from space.lib.constitution import write_constitution
from space.lib.mcp import registry
from space.lib.providers import claude, codex, gemini

from . import agents, sessions
from .environment import build_launch_env
from .prompt import spawn_prompt


def spawn_agent(identity: str, extra_args: list[str] | None = None):
    """Spawn an agent by identity from registry.

    Looks up agent, writes constitution to provider home dir,
    injects unified context via stdin, and executes the provider CLI.

    Args:
            identity: Agent identity from registry
            extra_args: Additional CLI arguments forwarded to provider
    """
    agent = agents.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found in registry")

    constitution_text = None
    if agent.constitution:
        const_path = paths.constitution(agent.constitution)
        constitution_text = const_path.read_text()

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
    session_id = sessions.create_session(agent.agent_id)

    context = spawn_prompt(identity, agent.model)
    has_prompt = bool(context.strip())

    provider_obj = {"claude": claude, "gemini": gemini, "codex": codex}.get(agent.provider)
    if provider_obj:
        if agent.provider == "gemini":
            launch_args = provider_obj.launch_args(has_prompt=has_prompt)
        else:
            launch_args = provider_obj.launch_args()
    else:
        launch_args = []

    mcp_args = []
    if agent.provider in ("claude", "codex"):
        mcp_config = registry.get_launch_config()
        if mcp_config:
            mcp_args = ["--mcp-config", json.dumps({"servers": mcp_config})]

    full_command = command_tokens + [context] + model_args + launch_args + mcp_args + passthrough
    display_command = command_tokens + ['"<space_manual>"'] + model_args + launch_args + passthrough

    click.echo(f"Executing: {' '.join(display_command)}")
    click.echo("")

    proc = subprocess.Popen(full_command, env=env, cwd=str(workspace_root))

    try:
        proc.wait()
    finally:
        sessions.end_session(session_id)


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
    """Write constitution to provider home dir."""
    write_constitution(provider, constitution)


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

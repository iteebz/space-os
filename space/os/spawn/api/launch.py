"""Agent launching: unified context injection, execute."""

import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click

from space.lib import paths
from space.lib.format import format_duration
from space.os import bridge, knowledge, memory

from . import agents, sessions


def build_spawn_context(identity: str, model: str | None = None) -> str:
    """Build unified prompt context for agent spawn.

    Includes: identity, spawn state, space-os interface, agent context, inbox.
    """

    parts = []

    agent = agents.get_agent(identity)
    if not agent:
        return f"You are {identity}."

    agent_id = agent.agent_id
    spawn_count = sessions.get_spawn_count(agent_id)
    wakes_this_spawn = sessions.get_wakes_this_spawn(agent_id)

    parts.append(f"You are {identity}.")
    if model:
        parts[0] += f" Your model is {model}."

    parts.append("")
    parts.append(f"🔄 Spawn #{spawn_count} • Woke {wakes_this_spawn} times this spawn")

    last_journal = memory.list_entries(identity, topic="journal", limit=1)
    if last_journal:
        e = last_journal[0]
        last_sleep_duration = format_duration(datetime.now().timestamp() - e.created_at)
        parts.append(f"📝 Last session {last_sleep_duration} ago")
    else:
        parts.append("📝 First spawn")

    parts.append("")
    parts.append("**space-os commands:**")
    parts.append("  space              — system orientation")
    parts.append("  spawn <agent>      — launch another agent")
    parts.append(f"  memory --as {identity}  — view/search your memories")
    parts.append(f"  bridge recv <channel> --as {identity}  — read channel messages")

    if agent.description:
        parts.append("")
        parts.append(f"**Your identity:** {agent.description}")

    core_entries = memory.list_entries(identity, filter="core")
    if core_entries:
        parts.append("")
        parts.append("⭐ **Core memories:**")
        for e in core_entries[:3]:
            parts.append(f"  [{e.memory_id[-8:]}] {e.message}")

    recent = memory.list_entries(identity, filter="recent:7", limit=3)
    non_journal = [e for e in recent if e.topic != "journal"]
    if non_journal:
        parts.append("")
        parts.append("📋 **Recent work (7d):**")
        for e in non_journal:
            ts = datetime.fromtimestamp(e.created_at).strftime("%m-%d %H:%M")
            parts.append(f"  [{ts}] {e.topic}: {e.message[:100]}")

    critical = _get_critical_knowledge()
    if critical:
        parts.append("")
        parts.append(f"💡 **Latest decision:** [{critical.domain}] {critical.content[:100]}")

    inbox_channels = bridge.fetch_inbox(agent_id)
    if inbox_channels:
        parts.append("")
        total_msgs = sum(ch.unread_count for ch in inbox_channels)
        parts.append(f"📬 **{total_msgs} unread messages in {len(inbox_channels)} channels:**")
        priority_ch = _priority_channel(inbox_channels)
        if priority_ch:
            parts.append(f"  #{priority_ch.name} ({priority_ch.unread_count} unread) ← START HERE")
            for ch in inbox_channels[:4]:
                if ch.name != priority_ch.name:
                    parts.append(f"  #{ch.name} ({ch.unread_count} unread)")
        else:
            for ch in inbox_channels[:5]:
                parts.append(f"  #{ch.name} ({ch.unread_count} unread)")
        if len(inbox_channels) > 5:
            parts.append(f"  ... and {len(inbox_channels) - 5} more")

    parts.append("")
    parts.append("**When you finish work:**")
    parts.append(f'  memory save "journal" "<summary>" --as {identity}')
    parts.append(f'  Then: bridge send <channel> --as {identity} "<message>"')

    parts.append("")
    paths.space_root() / "MANUAL.md"
    parts.append("**Full instruction set:** Read MANUAL.md")
    parts.append(f"  As {identity}, consult @space-os/MANUAL.md for all commands and workflows.")

    return "\n".join(parts)


def _get_critical_knowledge():
    """Get most recent critical knowledge entry (24h)."""
    critical_domains = {"decision", "architecture", "operations", "consensus"}
    entries = knowledge.list_entries()

    cutoff = datetime.now() - timedelta(hours=24)
    recent = [
        e
        for e in entries
        if e.domain in critical_domains and datetime.fromisoformat(e.created_at) > cutoff
    ]

    return recent[0] if recent else None


def _priority_channel(channels):
    """Identify highest priority channel."""
    if not channels:
        return None

    feedback_channel = next(
        (ch for ch in channels if ch.name == "space-feedback" and ch.unread_count > 0), None
    )
    if feedback_channel:
        return feedback_channel

    return max(channels, key=lambda ch: (ch.unread_count, ch.last_activity or ""))


def launch_agent(identity: str, extra_args: list[str] | None = None):
    """Launch an agent by identity from registry.

    Looks up agent, writes constitution to provider home dir,
    injects unified context via stdin, and executes the provider CLI.

    Args:
        identity: Agent identity from registry
        extra_args: Additional CLI arguments forwarded to provider
    """
    from . import sessions

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
    env = _build_launch_env()
    workspace_root = paths.space_root()
    env["PWD"] = str(workspace_root)
    command_tokens[0] = _resolve_executable(command_tokens[0], env)

    passthrough = extra_args or []
    model_args = ["--model", agent.model]
    tool_args = ["--disallowedTools", "Task"] if agent.provider == "claude" else []

    click.echo(f"Spawning {identity}...\n")
    session_id = sessions.create_session(agent.agent_id)

    stdin_content = build_spawn_context(identity, agent.model)

    full_command = command_tokens + model_args + tool_args + passthrough

    click.echo(f"Executing: {' '.join(full_command)}")
    click.echo("")

    proc = subprocess.Popen(
        full_command, env=env, cwd=str(workspace_root), stdin=subprocess.PIPE, text=True
    )
    proc.stdin.write(stdin_content + "\n")
    proc.stdin.close()
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

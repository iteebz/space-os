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
from space.lib.constitution import write_constitution
from space.lib.format import format_duration
from space.lib.providers import claude, codex, gemini
from space.os import bridge, knowledge, memory

from . import agents, sessions


def spawn_prompt(identity: str, model: str | None = None) -> str:
    """Build unified prompt context from MANUAL.md template with agent context filled in.

    Replaces <identity> placeholders and inserts agent-specific context blocks.
    """
    agent = agents.get_agent(identity)
    if not agent:
        return f"You are {identity}."

    agent_id = agent.agent_id

    manual_path = paths.package_root().parent / "MANUAL.md"
    if not manual_path.exists():
        return f"You are {identity}."

    manual_text = manual_path.read_text()

    spawn_count = sessions.get_spawn_count(agent_id)

    last_journal = memory.list_entries(identity, topic="journal", limit=1)
    if last_journal:
        e = last_journal[0]
        last_sleep_duration = format_duration(datetime.now().timestamp() - e.created_at)
        spawn_status = f"📝 Last session {last_sleep_duration} ago"
    else:
        spawn_status = "📝 First spawn"

    template_vars = {
        "identity": identity,
        "spawn_count": spawn_count,
        "spawn_status": spawn_status,
        "model": f" Your model is {model}." if model else "",
    }

    output = manual_text
    for var, value in template_vars.items():
        output = output.replace(f"<{var}>", str(value))

    agent_info_blocks = _build_agent_info_blocks(identity, agent, agent_id)
    return output.replace("{{AGENT_INFO}}", agent_info_blocks)


def _build_agent_info_blocks(identity: str, agent, agent_id: str) -> str:
    """Build identity, memories, and bridge context blocks for template injection."""
    parts = []

    if agent.description:
        parts.append(f"**Your identity:** {agent.description}")
        parts.append("")

    core_entries = memory.list_entries(identity, filter="core")
    if core_entries:
        parts.append("⭐ **Core memories:**")
        for e in core_entries[:3]:
            parts.append(f"  [{e.memory_id[-8:]}] {e.message}")
        parts.append("")

    recent = memory.list_entries(identity, filter="recent:7", limit=3)
    non_journal = [e for e in recent if e.topic != "journal"]
    if non_journal:
        parts.append("📋 **Recent work (7d):**")
        for e in non_journal:
            ts = datetime.fromtimestamp(e.created_at).strftime("%m-%d %H:%M")
            parts.append(f"  [{ts}] {e.topic}: {e.message[:100]}")
        parts.append("")

    critical = _get_critical_knowledge()
    if critical:
        parts.append(f"💡 **Latest decision:** [{critical.domain}] {critical.content[:100]}")
        parts.append("")

    inbox_channels = bridge.fetch_inbox(agent_id)
    if inbox_channels:
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


def spawn_agent(identity: str, extra_args: list[str] | None = None):
    """Spawn an agent by identity from registry.

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
    full_command = command_tokens + [context] + model_args + launch_args + passthrough
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

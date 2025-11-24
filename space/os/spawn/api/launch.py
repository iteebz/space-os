"""Agent launching: provider execution and lifecycle management."""

import contextlib
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

SPAWN_TIMEOUT = 300

PROVIDERS = {
    "claude": Claude,
    "gemini": Gemini,
    "codex": Codex,
}


def _start_session_discovery(spawn, agent):
    """Start background thread to discover and link session."""
    import threading
    import time

    def link_session():
        try:
            for _ in range(30):
                time.sleep(1)
                session_id = _discover_recent_session(agent.provider, spawn.created_at)
                if session_id:
                    spawns.link_session_to_spawn(spawn.id, session_id)
                    return
        except Exception as e:
            logger.debug(f"Session linking failed: {e}")

    threading.Thread(target=link_session, daemon=True).start()


def spawn_interactive(
    identity: str,
    extra_args: list[str] | None = None,
    resume: str | None = None,
):
    agent = agents.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found in registry")

    constitution_hash = agents.compute_constitution_hash(agent.constitution)
    env = build_launch_env()
    env["PWD"] = str(paths.space_root())

    executable = _resolve_executable(agent.provider, env)
    passthrough = extra_args or []

    typer.echo(f"Spawning {identity}...\n")
    spawn = spawns.create_spawn(
        agent_id=agent.agent_id,
        is_ephemeral=bool(passthrough),
        constitution_hash=constitution_hash,
        parent_spawn_id=None,
    )

    constitute(spawn, agent)
    env["SPACE_SPAWN_ID"] = spawn.id

    known_session_id = resolve_session_id(agent.agent_id, resume)
    if known_session_id:
        spawns.link_session_to_spawn(spawn.id, known_session_id)
        _copy_bookmarks_from_session(known_session_id, spawn.id)

    cwd = str(paths.identity_dir(agent.identity) if passthrough else paths.space_root())
    context = build_spawn_context(identity, task=passthrough[0] if passthrough else None)

    base_command = [executable] + _build_spawn_command(
        agent, known_session_id, resume is None and known_session_id, is_task=bool(passthrough)
    )[1:]  # Skip provider name, use resolved executable

    if passthrough:
        full_command = base_command + [context]
        display_command = base_command + ['"<context>"']
        typer.echo(f"Executing: {' '.join(display_command)}")
        typer.echo(f"Task: {passthrough[0]}\n")
        proc = subprocess.Popen(full_command, env=env, cwd=cwd)
    else:
        typer.echo(f"Executing: echo <context> | {' '.join(base_command)}\n")
        shell_cmd = f"echo {shlex.quote(context)} | {' '.join(base_command)}"
        proc = subprocess.Popen(shell_cmd, shell=True, env=env, cwd=cwd)

    if not known_session_id:
        _start_session_discovery(spawn, agent)

    try:
        proc.wait()
    finally:
        spawns.end_spawn(spawn.id)


def _discover_recent_session(provider: str, after_timestamp: str) -> str | None:
    """Find most recent session file created after timestamp."""
    from datetime import datetime

    if provider == "claude":
        sessions_dir = Claude.SESSIONS_DIR
    else:
        return None

    if not sessions_dir.exists():
        return None

    after_dt = datetime.fromisoformat(after_timestamp.replace("Z", "+00:00"))
    if after_dt.tzinfo:
        after_dt = after_dt.replace(tzinfo=None)
    best_match = None
    best_time = None

    for jsonl in sessions_dir.rglob("*.jsonl"):
        try:
            ctime = datetime.fromtimestamp(jsonl.stat().st_birthtime)
            if ctime > after_dt and (best_time is None or ctime > best_time):
                session_id = Claude.session_id_from_contents(jsonl)
                if not session_id:
                    session_id = jsonl.stem  # Fallback to filename
                best_match = session_id
                best_time = ctime
        except (OSError, ValueError, AttributeError):
            continue

    return best_match


def spawn_ephemeral(
    identity: str,
    instruction: str,
    channel_id: str,
    resume: str | None = None,
):
    from space.os.bridge.api import channels

    agent = agents.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found in registry")
    if not agent.model:
        raise ValueError(f"Agent '{identity}' has no model (human identity, cannot spawn)")

    parent_spawn_id = os.environ.get("SPACE_SPAWN_ID")
    if parent_spawn_id:
        parent_spawn = spawns.get_spawn(parent_spawn_id)
        if parent_spawn:
            depth = spawns.get_spawn_depth(parent_spawn_id)
            if depth >= spawns.MAX_SPAWN_DEPTH:
                raise ValueError(
                    f"Cannot spawn: max depth {spawns.MAX_SPAWN_DEPTH} reached (current depth: {depth})"
                )
        else:
            parent_spawn_id = None

    constitution_hash = agents.compute_constitution_hash(agent.constitution)

    spawn = spawns.create_spawn(
        agent_id=agent.agent_id,
        is_ephemeral=True,
        channel_id=channel_id,
        constitution_hash=constitution_hash,
        parent_spawn_id=parent_spawn_id,
    )
    spawns.update_status(spawn.id, "running")

    constitute(spawn, agent)

    env = build_launch_env()
    env["SPACE_SPAWN_ID"] = spawn.id
    env["SPACE_AGENT_IDENTITY"] = identity

    channel = channels.get_channel(channel_id) if channel_id else None
    channel_name = channel.name if channel else None

    session_id = resolve_session_id(agent.agent_id, resume, channel_id=channel_id)
    is_continue = resume is None and session_id

    if session_id:
        _copy_bookmarks_from_session(session_id, spawn.id)

    try:
        _run_ephemeral(agent, instruction, spawn, channel_name, session_id, is_continue, env)
        spawns.update_status(spawn.id, "completed")
        return spawn
    except Exception as e:
        logger.error(f"Headless spawn failed for {identity}: {e}", exc_info=True)
        spawns.update_status(spawn.id, "failed")
        raise
    finally:
        spawns.end_spawn(spawn.id)


def _run_ephemeral(
    agent,
    instruction: str,
    spawn,
    channel_name: str | None,
    session_id: str | None,
    is_continue: bool,
    env: dict[str, str],
) -> None:
    context = build_spawn_context(
        agent.identity, task=instruction, channel=channel_name, is_ephemeral=True
    )
    cmd = _build_spawn_command(agent, session_id, is_continue)
    stdout = _execute_spawn(cmd, context, agent, env)
    _link_session_if_needed(spawn, session_id, agent.provider)
    _send_output_to_channel(stdout, agent, channel_name)


def _parse_model_and_effort(agent) -> tuple[str, str | None]:
    """Extract model ID and reasoning effort (codex only)."""
    if agent.provider == "codex":
        return Codex.parse_model_id(agent.model)
    return agent.model, None


def _build_launch_args(agent, is_task: bool, reasoning_effort: str | None) -> list[str]:
    """Build provider-specific launch arguments."""
    provider_class = PROVIDERS.get(agent.provider)
    if not provider_class:
        raise ValueError(f"Unknown provider: {agent.provider}")

    if is_task:
        if agent.provider == "codex":
            return provider_class.task_launch_args(reasoning_effort=reasoning_effort)
        return provider_class.task_launch_args()

    if agent.provider == "gemini":
        return provider_class.launch_args(has_prompt=False)
    if agent.provider == "claude":
        return provider_class.launch_args(is_ephemeral=False)
    if agent.provider == "codex":
        return provider_class.launch_args(reasoning_effort=reasoning_effort)
    return provider_class.launch_args()


def _build_spawn_command(
    agent, session_id: str | None, is_continue: bool, is_task: bool = True
) -> list[str]:
    """Assemble provider command for spawn execution."""
    model_id, reasoning_effort = _parse_model_and_effort(agent)
    launch_args = _build_launch_args(agent, is_task, reasoning_effort)
    model_args = ["--model", model_id]
    add_dir_args = ["--add-dir", str(paths.space_root())] if agent.provider != "codex" else []
    resume_args = _build_resume_args(agent.provider, session_id, is_continue)

    if agent.provider == "codex":
        return ["codex"] + resume_args + ["exec"] + launch_args + model_args
    return [agent.provider] + model_args + launch_args + add_dir_args + resume_args


def _execute_spawn(cmd: list[str], context: str, agent, env: dict[str, str]) -> str:
    import tempfile

    spawn_dir = paths.identity_dir(agent.identity)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(context)
        context_file = f.name

    try:
        with open(context_file) as stdin_file:
            proc = subprocess.Popen(
                cmd,
                stdin=stdin_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(spawn_dir),
                env=env,
            )
            stdout, stderr = proc.communicate(timeout=SPAWN_TIMEOUT)

        if proc.returncode != 0:
            raise RuntimeError(f"{agent.provider.title()} spawn failed: {stderr}")

        return stdout

    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError(f"{agent.provider.title()} spawn timed out") from None
    finally:
        import os

        with contextlib.suppress(Exception):
            os.unlink(context_file)


def _link_session_if_needed(spawn, session_id: str | None, provider: str) -> None:
    from space.os.sessions.api import linker

    if session_id:
        linker.link_spawn_to_session(spawn.id, session_id)
    else:
        try:
            discovered_session_id = _discover_recent_session(provider, spawn.created_at)
            if discovered_session_id:
                linker.link_spawn_to_session(spawn.id, discovered_session_id)
        except Exception as e:
            logger.debug(f"Session discovery failed (non-fatal): {e}")


def _send_output_to_channel(stdout: str, agent, channel_name: str | None) -> None:
    if not channel_name or not stdout.strip():
        return

    if agent.provider == "codex":
        output_text = _parse_codex_output(stdout)
    else:
        output_text = stdout.strip()

    if output_text:
        import asyncio

        from space.os.bridge.api import messaging

        asyncio.run(messaging.send_message(channel_name, agent.identity, output_text))


def _parse_codex_output(jsonl_output: str) -> str:
    """Parse Codex JSONL output and extract agent message text."""
    import json

    messages = []
    for line in jsonl_output.strip().split("\n"):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if obj.get("type") == "item.completed":
                item = obj.get("item", {})
                if item.get("type") == "agent_message":
                    text = item.get("text", "")
                    if text:
                        messages.append(text)
        except json.JSONDecodeError:
            continue

    return "\n\n".join(messages) if messages else ""


def _get_launch_args(
    provider_class, provider: str, has_passthrough: bool, reasoning_effort: str | None
) -> list[str]:
    if not provider_class:
        return []
    if provider == "gemini":
        return provider_class.launch_args(has_prompt=has_passthrough)
    if provider == "claude":
        return provider_class.launch_args(is_ephemeral=has_passthrough)
    if provider == "codex":
        return provider_class.launch_args(reasoning_effort=reasoning_effort)
    return provider_class.launch_args()


def _resolve_executable(executable: str, env: dict[str, str]) -> str:
    if os.path.isabs(executable):
        return executable

    search_path = env.get("PATH") or None
    resolved = shutil.which(executable, path=search_path)
    if not resolved:
        raise ValueError(f"Executable '{executable}' not found on PATH")
    return resolved


def _build_resume_args(provider: str, session_id: str | None, is_continue: bool) -> list[str]:
    if not session_id:
        return []

    if provider == "claude":
        return ["-r", session_id]

    if provider == "codex":
        return ["resume", session_id]

    return []


def _copy_bookmarks_from_session(session_id: str, new_spawn_id: str) -> None:
    from space.lib import store

    with store.ensure() as conn:
        row = conn.execute(
            "SELECT id FROM spawns WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()

        if row:
            previous_spawn_id = row[0]
            from space.os.bridge.api.messaging import copy_bookmarks

            copy_bookmarks(previous_spawn_id, new_spawn_id)

"""Agent launching: provider execution and lifecycle management."""

import logging
import os
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

    model_id = agent.model
    reasoning_effort = None
    if agent.provider == "codex":
        model_id, reasoning_effort = Codex.parse_model_id(agent.model)

    model_args = ["--model", model_id]

    typer.echo(f"Spawning {identity}...\n")
    spawn = spawns.create_spawn(
        agent_id=agent.agent_id,
        is_ephemeral=bool(passthrough),
        constitution_hash=constitution_hash,
        parent_spawn_id=None,
    )

    constitute(spawn, agent)

    env["SPACE_SPAWN_ID"] = spawn.id

    provider_class = PROVIDERS.get(agent.provider)
    launch_args = _get_launch_args(
        provider_class, agent.provider, bool(passthrough), reasoning_effort
    )

    add_dir_args = ["--add-dir", str(paths.space_root())]

    known_session_id = resolve_session_id(agent.agent_id, resume)
    resume_args = _build_resume_args(
        agent.provider, known_session_id, resume is None and known_session_id
    )

    if known_session_id:
        spawns.link_session_to_spawn(spawn.id, known_session_id)
        _copy_bookmarks_from_session(known_session_id, spawn.id)

    context = build_spawn_context(identity, task=passthrough[0] if passthrough else None)

    full_command = [executable] + add_dir_args + [context] + model_args + launch_args + resume_args
    display_command = (
        [executable] + add_dir_args + ['"<context>"'] + model_args + launch_args + resume_args
    )

    typer.echo(f"Executing: {' '.join(display_command)}")
    typer.echo("")

    cwd = str(paths.identity_dir(agent.identity) if passthrough else paths.space_root())

    proc = subprocess.Popen(full_command, env=env, cwd=cwd)

    # Link session as soon as Claude creates the JSONL (only for new sessions)
    if not known_session_id:
        import threading
        import time

        def link_session():
            try:
                for _ in range(30):  # Try for 30 seconds
                    time.sleep(1)
                    session_id = _discover_recent_session(agent.provider, spawn.created_at)
                    if session_id:
                        spawns.link_session_to_spawn(spawn.id, session_id)
                        return
            except Exception as e:
                logger.debug(f"Session linking failed: {e}")

        linker_thread = threading.Thread(target=link_session, daemon=True)
        linker_thread.start()

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

    os.environ["SPACE_SPAWN_ID"] = spawn.id

    channel = channels.get_channel(channel_id) if channel_id else None
    channel_name = channel.name if channel else None

    session_id = resolve_session_id(agent.agent_id, resume)
    is_continue = resume is None and session_id

    if session_id:
        _copy_bookmarks_from_session(session_id, spawn.id)

    try:
        _run_ephemeral(agent, instruction, spawn, channel_name, session_id, is_continue)
        spawns.update_status(spawn.id, "completed")
        return spawn
    except Exception as e:
        logger.error(f"Headless spawn failed for {identity}: {e}", exc_info=True)
        spawns.update_status(spawn.id, "failed")
        raise


def _run_ephemeral(
    agent,
    instruction: str,
    spawn,
    channel_name: str | None,
    session_id: str | None,
    is_continue: bool,
) -> None:
    from space.os.sessions.api import linker, sync

    provider = agent.provider
    provider_class = PROVIDERS.get(provider)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider}")

    if provider == "codex":
        model_id, reasoning_effort = Codex.parse_model_id(agent.model)
        launch_args = provider_class.task_launch_args(reasoning_effort=reasoning_effort)
        model_args = ["--model", model_id]
    else:
        launch_args = provider_class.task_launch_args()
        model_args = []

    context = build_spawn_context(
        agent.identity, task=instruction, channel=channel_name, is_ephemeral=True
    )
    add_dir_args = ["--add-dir", str(paths.space_root())]
    resume_args = _build_resume_args(provider, session_id, is_continue)

    if provider == "codex":
        cmd = ["codex"] + resume_args + ["exec"] + launch_args + model_args + add_dir_args
    else:
        cmd = [provider] + launch_args + add_dir_args + resume_args

    spawn_dir = paths.identity_dir(agent.identity)

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(spawn_dir),
    )

    try:
        provider_session_id = None
        proc.stdin.write(context)
        proc.stdin.close()

        for line in proc.stdout:
            if not line.strip():
                continue

            if not provider_session_id:
                provider_session_id = provider_class.session_id_from_stream(line)
                if provider_session_id:
                    linker.link_spawn_to_session(spawn.id, provider_session_id)

            if provider_session_id:
                try:
                    sync.ingest(provider_session_id)
                except Exception as e:
                    logger.debug(f"Ingest error (non-fatal): {e}")

        proc.wait(timeout=SPAWN_TIMEOUT)

        if proc.returncode != 0:
            stderr = proc.stderr.read()
            raise RuntimeError(f"{provider.title()} spawn failed: {stderr}")

        if not provider_session_id:
            raise RuntimeError(f"No session_id in {provider.title()} output stream")

    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError(f"{provider.title()} spawn timed out") from None


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
        return ["-c"] if is_continue else ["-r", session_id]

    if provider == "codex":
        return ["resume", "--last"] if is_continue else ["resume", session_id]

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

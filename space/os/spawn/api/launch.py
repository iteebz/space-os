"""Agent launching: provider execution and lifecycle management."""

import contextlib
import logging
import os
import subprocess

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


def _discover_recent_session(provider: str, after_timestamp: str) -> str | None:
    """Find most recent session file created after timestamp."""
    from datetime import datetime

    provider_cls = PROVIDERS.get(provider)
    if not provider_cls:
        return None

    sessions_dir = getattr(provider_cls, "SESSIONS_DIR", None)
    if not sessions_dir or not sessions_dir.exists():
        return None

    extractor = getattr(provider_cls, "session_id_from_contents", None)
    file_pattern = getattr(provider_cls, "SESSION_FILE_PATTERN", "*.jsonl")

    try:
        after_dt = datetime.fromisoformat(after_timestamp.replace("Z", "+00:00"))
        if after_dt.tzinfo:
            after_dt = after_dt.replace(tzinfo=None)
        after_ts = after_dt.timestamp()
    except (ValueError, AttributeError):
        after_ts = 0

    best_match = None
    best_time = None

    for session_file in sessions_dir.rglob(file_pattern):
        try:
            stat = session_file.stat()
            file_time = getattr(stat, "st_birthtime", None) or stat.st_mtime
            if file_time <= after_ts:
                continue
            if best_time is None or file_time > best_time:
                session_id = extractor(session_file) if extractor else None
                if not session_id:
                    session_id = session_file.stem
                best_match = session_id
                best_time = file_time
        except (OSError, ValueError, AttributeError):
            continue

    return best_match


def spawn_ephemeral(
    identity: str,
    instruction: str,
    channel_id: str,
    resume: str | None = None,
    max_retries: int = 1,
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
        channel_id=channel_id,
        constitution_hash=constitution_hash,
        parent_spawn_id=parent_spawn_id,
    )
    spawns.update_status(spawn.id, "running")

    constitute(spawn, agent)

    env = build_launch_env()
    env["SPACE_SPAWN_ID"] = spawn.id
    env["SPACE_IDENTITY"] = identity

    channel = channels.get_channel(channel_id) if channel_id else None
    channel_name = channel.name if channel else None

    session_id = resolve_session_id(
        agent.agent_id,
        resume,
        channel_id=channel_id,
        provider=agent.provider,
        identity=agent.identity,
    )
    is_continue = resume is None and session_id

    if session_id:
        _copy_bookmarks_from_session(session_id, spawn.id)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            _run_ephemeral(agent, instruction, spawn, channel_name, session_id, is_continue, env)
            spawns.update_status(spawn.id, "completed")
            return spawn
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"Spawn {identity} failed (attempt {attempt + 1}), retrying: {e}")
                continue
            logger.error(f"Spawn {identity} failed after {max_retries + 1} attempts: {e}")
            spawns.update_status(spawn.id, "failed")
            raise
        finally:
            if attempt == max_retries or last_error is None:
                spawns.end_spawn(spawn.id)
    return None


def _run_ephemeral(
    agent,
    instruction: str,
    spawn,
    channel_name: str | None,
    session_id: str | None,
    is_continue: bool,
    env: dict[str, str],
) -> None:
    instruction_text, image_paths = _extract_images_from_instruction(instruction)
    context = build_spawn_context(
        agent.identity,
        task=instruction_text,
        channel=channel_name,
    )
    cmd = _build_spawn_command(agent, session_id, is_continue, image_paths=image_paths)
    _execute_spawn(cmd, context, agent, spawn.id, env)
    _link_session(spawn, session_id, agent.provider)


def _parse_model_and_effort(agent) -> tuple[str, str | None]:
    """Extract model ID and reasoning effort (codex only)."""
    if agent.provider == "codex":
        return Codex.parse_model_id(agent.model)
    return agent.model, None


def _build_launch_args(
    agent, is_task: bool, reasoning_effort: str | None, image_paths: list[str] | None = None
) -> list[str]:
    """Build provider-specific launch arguments."""
    provider_class = PROVIDERS.get(agent.provider)
    if not provider_class:
        raise ValueError(f"Unknown provider: {agent.provider}")

    if is_task:
        if agent.provider == "codex":
            return provider_class.task_launch_args(
                reasoning_effort=reasoning_effort, image_paths=image_paths
            )
        return provider_class.task_launch_args()

    if agent.provider == "gemini":
        return provider_class.launch_args(has_prompt=False)
    if agent.provider == "claude":
        return provider_class.launch_args()
    if agent.provider == "codex":
        return provider_class.launch_args(reasoning_effort=reasoning_effort)
    return provider_class.launch_args()


def _build_spawn_command(
    agent,
    session_id: str | None,
    is_continue: bool,
    is_task: bool = True,
    image_paths: list[str] | None = None,
) -> list[str]:
    """Assemble provider command for spawn execution."""
    model_id, reasoning_effort = _parse_model_and_effort(agent)
    launch_args = _build_launch_args(agent, is_task, reasoning_effort, image_paths)
    model_args = ["--model", model_id]
    if agent.provider == "codex":
        add_dir_args: list[str] = []
    elif agent.provider == "gemini":
        # Gemini CLI uses --include-directories instead of --add-dir.
        add_dir_args = ["--include-directories", str(paths.space_root())]
    else:
        add_dir_args = ["--add-dir", str(paths.space_root())]
    resume_args = _build_resume_args(agent.provider, session_id, is_continue)

    if agent.provider == "codex":
        return ["codex"] + resume_args + ["exec"] + launch_args + model_args
    return [agent.provider] + launch_args + model_args + add_dir_args + resume_args


def _execute_spawn(cmd: list[str], context: str, agent, spawn_id: str, env: dict[str, str]) -> str:
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
            spawns.set_pid(spawn_id, proc.pid)
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


def _link_session(spawn, session_id: str | None, provider: str) -> None:
    """Link spawn to session (only if session_id explicitly provided)."""
    from space.os.sessions.api import linker

    try:
        if session_id:
            linker.link_spawn_to_session(spawn.id, session_id)
    except Exception as e:
        logger.debug(f"Session linking failed (non-fatal): {e}")


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

    if provider == "gemini":
        # Gemini uses index-based resume (--resume 1, --resume latest), not session_id.
        # Skip resume for now; session linking still works for observability.
        return []

    return []


def _extract_images_from_instruction(instruction: str) -> tuple[str, list[str]]:
    """Extract image paths from instruction text.

    ComposeBox formats images as 'Image: /path/to/image.png' lines at start.
    Returns (clean_instruction, image_paths).
    """
    lines = instruction.split("\n")
    image_paths = []
    content_lines = []

    for line in lines:
        if line.strip().startswith("Image:"):
            path = line.strip()[6:].strip()
            # Expand ~ to full path
            if path.startswith("~"):
                from pathlib import Path

                path = str(Path(path).expanduser())
            image_paths.append(path)
        else:
            content_lines.append(line)

    clean_instruction = "\n".join(content_lines).strip()
    return clean_instruction, image_paths


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

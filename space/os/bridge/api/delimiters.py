"""Bridge delimiter parsing: @spawn, !control, #channels, /docs."""

import atexit
import logging
import queue
import re
import threading

from space.os.spawn.api import agents as spawn_agents
from space.os.spawn.api import spawns
from space.os.spawn.api.launch import spawn_ephemeral

log = logging.getLogger(__name__)

_spawn_queue: queue.Queue = queue.Queue(maxsize=1000)
_worker_thread: threading.Thread | None = None
_shutdown_flag = threading.Event()


def _start_worker() -> None:
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return

    def _process_spawn_queue():
        while not _shutdown_flag.is_set():
            try:
                channel_id, content, agent_id = _spawn_queue.get(timeout=0.5)
                try:
                    from . import channels

                    channel = channels.get_channel(channel_id)
                    if not channel:
                        log.error(f"Channel {channel_id} not found")
                        continue
                    _process_control_commands_impl(channel_id, content)
                    _process_mentions(channel_id, content, agent_id)
                except Exception as e:
                    log.error(f"Failed to process delimiters: {e}", exc_info=True)
                finally:
                    _spawn_queue.task_done()
            except queue.Empty:
                continue

    _worker_thread = threading.Thread(target=_process_spawn_queue, daemon=True, name="spawn-worker")
    _worker_thread.start()
    log.info("Spawn worker thread started")


def _shutdown_worker() -> None:
    if _worker_thread is None or not _worker_thread.is_alive():
        return

    log.info("Shutting down spawn worker...")
    _shutdown_flag.set()
    log.info("Spawn worker shutdown signaled (daemon will finish async)")


atexit.register(_shutdown_worker)


def _parse_mentions(content: str) -> list[str]:
    pattern = r"@([\w-]+)"
    matches = re.findall(pattern, content)
    return list(set(matches))


def _parse_control_commands(content: str) -> dict[str, list[str] | bool]:
    pause_pattern = r"!pause(?:\s+([\w-]+))?"
    resume_pattern = r"!resume(?:\s+([\w-]+))?"
    abort_pattern = r"!abort(?:\s+([\w-]+))?"

    pause_matches = re.findall(pause_pattern, content)
    resume_matches = re.findall(resume_pattern, content)
    abort_matches = re.findall(abort_pattern, content)

    bare_identity_pattern = r"!(?!pause|resume|abort)([\w-]+)"
    bare_identities = re.findall(bare_identity_pattern, content)

    pause_identities = [m for m in pause_matches if m]
    resume_identities = [m for m in resume_matches if m]
    abort_identities = [m for m in abort_matches if m]

    has_bare_pause = bool(re.search(r"!pause(?:\s|$|[^\w-])", content))
    has_bare_resume = bool(re.search(r"!resume(?:\s|$|[^\w-])", content))
    has_bare_abort = bool(re.search(r"!abort(?:\s|$|[^\w-])", content))

    all_pause_identities = pause_identities + bare_identities

    return {
        "pause_identities": all_pause_identities,
        "resume_identities": resume_identities,
        "abort_identities": abort_identities,
        "pause_all": has_bare_pause and not all_pause_identities,
        "resume_all": has_bare_resume and not resume_identities,
        "abort_all": has_bare_abort and not abort_identities,
    }


def _process_delimiters_worker(channel_id: str, content: str, agent_id: str | None) -> None:
    from . import channels
    
    channel = channels.get_channel(channel_id)
    if not channel:
        log.error(f"Channel {channel_id} not found")
        return
    
    try:
        _process_control_commands_impl(channel_id, content)
        _process_mentions(channel_id, content, agent_id)
    except Exception as e:
        log.error(f"Failed to process delimiters: {e}", exc_info=True)


def spawn_from_mentions(channel_id: str, content: str, agent_id: str | None = None) -> None:
    import subprocess
    import sys
    import base64
    import json
    
    # Spawn background process via subprocess to avoid blocking and db connection issues
    payload = json.dumps({"channel_id": channel_id, "content": content, "agent_id": agent_id})
    payload_b64 = base64.b64encode(payload.encode()).decode()
    
    subprocess.Popen(
        [sys.executable, "-c", f"""
import sys
import json
import base64
sys.path.insert(0, {repr(sys.path[0])})
from space.os.bridge.api.delimiters import _process_delimiters_worker

payload = json.loads(base64.b64decode({repr(payload_b64)}).decode())
_process_delimiters_worker(payload['channel_id'], payload['content'], payload['agent_id'])
"""],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )


def _process_control_commands_impl(channel_id: str, content: str) -> None:
    commands = _parse_control_commands(content)

    if commands["pause_all"]:
        _update_spawns_status(channel_id, None, "running", "pause")
    elif commands["pause_identities"]:
        for identity in commands["pause_identities"]:
            _update_spawns_status(channel_id, identity, "running", "pause")

    if commands["resume_all"]:
        _update_spawns_status(channel_id, None, "paused", "resume")
    elif commands["resume_identities"]:
        for identity in commands["resume_identities"]:
            _update_spawns_status(channel_id, identity, "paused", "resume")

    if commands["abort_all"]:
        _update_spawns_status(channel_id, None, "running", "abort")
    elif commands["abort_identities"]:
        for identity in commands["abort_identities"]:
            _update_spawns_status(channel_id, identity, "running", "abort")


def _abort_spawn(spawn_id: str) -> None:
    """Abort a running spawn - terminates task execution, agent identity preserved."""
    import contextlib
    import os
    import signal
    
    spawn_obj = spawns.get_spawn(spawn_id)
    if not spawn_obj:
        return
    
    if spawn_obj.pid:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(spawn_obj.pid, signal.SIGTERM)
    
    spawns.update_status(spawn_id, "killed")


def _update_spawns_status(
    channel_id: str, identity: str | None, from_status: str, action: str
) -> None:
    if identity is None:
        log.info(f"{action.title()}ing all {from_status} spawns in channel {channel_id}")
        spawn_list = spawns.get_channel_spawns(channel_id, status=from_status)
    else:
        agent = spawn_agents.get_agent(identity)
        if not agent:
            log.warning(f"Identity {identity} not found in registry")
            return

        log.info(f"{action.title()}ing {identity}")
        spawn_list = [
            s for s in spawns.get_spawns_for_agent(agent.agent_id) if s.status == from_status
        ]

        if not spawn_list:
            log.info(f"No {from_status} spawns for {identity}")
            return

    if action == "pause":
        action_fn = spawns.pause_spawn
    elif action == "resume":
        action_fn = spawns.resume_spawn
    elif action == "abort":
        action_fn = _abort_spawn
    else:
        log.warning(f"Unknown action: {action}")
        return

    for spawn_obj in spawn_list:
        try:
            action_fn(spawn_obj.id)
            suffix = f" for {identity}" if identity else ""
            log.info(f"{action.title()}d spawn {spawn_obj.id[:8]}{suffix}")
        except ValueError as e:
            log.warning(f"Could not {action} spawn {spawn_obj.id[:8]}: {e}")


def _process_mentions(channel_id: str, content: str, sender_agent_id: str | None = None) -> None:
    log.info(f"Processing channel={channel_id}, content={content[:50]}")

    mentions = _parse_mentions(content)
    log.info(f"Found mentions: {mentions}")
    if not mentions:
        log.info("No mentions, skipping")
        return

    if sender_agent_id:
        log.info(f"Skipping mentions from sender agent: {sender_agent_id}")
        mentions = [
            m
            for m in mentions
            if (agent := spawn_agents.get_agent(m)) and agent.agent_id != sender_agent_id
        ]
        if not mentions:
            log.info("All mentions were from sender, skipping")
            return

    for identity in mentions:
        agent = spawn_agents.get_agent(identity)
        if not agent:
            log.warning(f"Identity {identity} not found in registry")
            continue
        
        # Skip human mentions - humans can't spawn
        if identity == "human" or not agent.model:
            log.info(f"Skipping @{identity} mention (human identity)")
            continue

        paused_spawns = spawns.get_spawns_for_agent(agent.agent_id, status="paused")

        if paused_spawns:
            most_recent = max(paused_spawns, key=lambda s: s.created_at or "")
            try:
                spawns.resume_spawn(most_recent.id)
                log.info(f"Resumed paused spawn {most_recent.id[:8]} for {identity}")
                continue
            except ValueError as e:
                log.warning(f"Could not resume spawn for {identity}: {e}")

        try:
            log.info(f"Spawning {identity}")
            spawn_ephemeral(identity, instruction=content, channel_id=channel_id)
            log.info(f"Spawned {identity} successfully")
        except Exception as e:
            log.error(f"Spawn error for {identity}: {e}")

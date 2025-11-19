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

    log.info("Shutting down spawn worker (draining queue)...")
    _shutdown_flag.set()
    _spawn_queue.join()
    _worker_thread.join(timeout=5)
    log.info("Spawn worker shutdown complete")


atexit.register(_shutdown_worker)


def _parse_mentions(content: str) -> list[str]:
    pattern = r"@([\w-]+)"
    matches = re.findall(pattern, content)
    return list(set(matches))


def _parse_control_commands(content: str) -> dict[str, list[str] | bool]:
    pause_pattern = r"!pause(?:\s+([\w-]+))?"
    resume_pattern = r"!resume(?:\s+([\w-]+))?"

    pause_matches = re.findall(pause_pattern, content)
    resume_matches = re.findall(resume_pattern, content)

    bare_identity_pattern = r"!(?!pause|resume)([\w-]+)"
    bare_identities = re.findall(bare_identity_pattern, content)

    pause_identities = [m for m in pause_matches if m]
    resume_identities = [m for m in resume_matches if m]

    has_bare_pause = bool(re.search(r"!pause(?:\s|$|[^\w-])", content))
    has_bare_resume = bool(re.search(r"!resume(?:\s|$|[^\w-])", content))

    all_pause_identities = pause_identities + bare_identities

    return {
        "pause_identities": all_pause_identities,
        "resume_identities": resume_identities,
        "pause_all": has_bare_pause and not all_pause_identities,
        "resume_all": has_bare_resume and not resume_identities,
    }


def spawn_from_mentions(channel_id: str, content: str, agent_id: str | None = None) -> None:
    _start_worker()

    try:
        _spawn_queue.put_nowait((channel_id, content, agent_id))
    except queue.Full:
        log.error(f"Spawn queue full (1000 items), dropping request for channel {channel_id}")


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

    action_fn = spawns.pause_spawn if action == "pause" else spawns.resume_spawn

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

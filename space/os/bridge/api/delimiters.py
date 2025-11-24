"""Bridge delimiter parsing: @spawn, !control, #channels, /docs."""

import contextlib
import logging
import re

from space.os.spawn.api import agents as spawn_agents
from space.os.spawn.api import spawns
from space.os.spawn.api.launch import spawn_ephemeral

log = logging.getLogger(__name__)


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


async def process_delimiters(channel_id: str, content: str, agent_id: str | None = None) -> None:
    """Process delimiters asynchronously.

    Fire-and-forget async task for:
    - Parsing !pause, !resume, !abort control commands
    - Spawning agents from @mentions
    - Non-blocking bridge message sending
    """
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
        spawn_list = spawns.get_channel_spawns(channel_id, status=from_status)
    else:
        agent = spawn_agents.get_agent(identity)
        if not agent:
            return

        spawn_list = [
            s for s in spawns.get_spawns_for_agent(agent.agent_id) if s.status == from_status
        ]

        if not spawn_list:
            return

    if action == "pause":
        action_fn = spawns.pause_spawn
    elif action == "resume":
        action_fn = spawns.resume_spawn
    elif action == "abort":
        action_fn = _abort_spawn
    else:
        return

    for spawn_obj in spawn_list:
        with contextlib.suppress(ValueError):
            action_fn(spawn_obj.id)


def _process_mentions(channel_id: str, content: str, sender_agent_id: str | None = None) -> None:
    mentions = _parse_mentions(content)
    if not mentions:
        return

    if sender_agent_id:
        mentions = [
            m
            for m in mentions
            if (agent := spawn_agents.get_agent(m)) and agent.agent_id != sender_agent_id
        ]
        if not mentions:
            return

    for identity in mentions:
        agent = spawn_agents.get_agent(identity)
        if not agent:
            continue

        if identity == "human" or not agent.model:
            continue

        paused_spawns = spawns.get_spawns_for_agent(agent.agent_id, status="paused")

        if paused_spawns:
            most_recent = max(paused_spawns, key=lambda s: s.created_at or "")
            try:
                spawns.resume_spawn(most_recent.id)
                continue
            except ValueError:
                pass

        try:
            spawn_ephemeral(identity, instruction=content, channel_id=channel_id)
        except Exception as e:
            log.error(f"Spawn error for {identity}: {e}")

"""Agent spawning: @mentions and task orchestration."""

import logging
import re

from space.os.spawn.api import agents as spawn_agents
from space.os.spawn.api import spawns
from space.os.spawn.api.launch import spawn_ephemeral

log = logging.getLogger(__name__)


def _parse_mentions(content: str) -> list[str]:
    """Extract @identity mentions from content."""
    pattern = r"@([\w-]+)"
    matches = re.findall(pattern, content)
    return list(set(matches))


def _parse_pause_commands(content: str) -> list[str]:
    """Extract !identity pause commands from content."""
    pattern = r"!([\w-]+)"
    matches = re.findall(pattern, content)
    return list(set(matches))


def spawn_from_mentions(channel_id: str, content: str, agent_id: str | None = None) -> None:
    """Process mentions and pause commands from message content (async, non-blocking).

    Args:
        channel_id: Channel where message was posted
        content: Message content with potential @mentions and !pauses
        agent_id: If provided, skip processing mentions from this agent (prevents cascades)
    """
    import threading

    def _process_async():
        try:
            from . import channels

            channel = channels.get_channel(channel_id)
            if not channel:
                log.error(f"Channel {channel_id} not found")
                return
            channel_name = channel.name
            _process_pause_commands(channel_id, channel_name, content)
            _process_mentions(channel_id, channel_name, content, agent_id)
        except Exception as e:
            log.error(f"Failed to process mentions/pauses: {e}")

    thread = threading.Thread(target=_process_async, daemon=True)
    thread.start()


def _process_pause_commands(channel_id: str, channel_name: str, content: str) -> None:
    """Process !identity pause commands."""
    pause_commands = _parse_pause_commands(content)
    log.info(f"Found pause commands: {pause_commands}")
    if not pause_commands:
        return

    for identity in pause_commands:
        log.info(f"Pausing {identity}")
        agent = spawn_agents.get_agent(identity)
        if not agent:
            log.warning(f"Identity {identity} not found in registry")
            continue

        paused_spawns = [
            s for s in spawns.get_spawns_for_agent(agent.agent_id) if s.status == "running"
        ]
        if not paused_spawns:
            log.info(f"No running spawns for {identity}")
            continue

        for spawn_obj in paused_spawns:
            try:
                spawns.pause_spawn(spawn_obj.id)
                log.info(f"Paused spawn {spawn_obj.id[:8]} for {identity}")
            except ValueError as e:
                log.warning(f"Could not pause {identity}: {e}")


def _process_mentions(
    channel_id: str, channel_name: str, content: str, sender_agent_id: str | None = None
) -> None:
    """Process @mentions: check for paused spawns first, then spawn or resume."""
    log.info(f"Processing channel={channel_name}, content={content[:50]}")

    mentions = _parse_mentions(content)
    log.info(f"Found mentions: {mentions}")
    if not mentions:
        log.info("No mentions, skipping")
        return

    if sender_agent_id:
        log.info(f"Skipping mentions from sender agent: {sender_agent_id}")
        filtered = []
        for m in mentions:
            agent = spawn_agents.get_agent(m)
            if agent and agent.agent_id != sender_agent_id:
                filtered.append(m)
        mentions = filtered
        if not mentions:
            log.info("All mentions were from sender, skipping")
            return

    for identity in mentions:
        agent = spawn_agents.get_agent(identity)
        if not agent:
            log.warning(f"Identity {identity} not found in registry")
            continue

        paused_spawns = [
            s for s in spawns.get_spawns_for_agent(agent.agent_id) if s.status == "paused"
        ]

        if paused_spawns:
            paused_spawn = paused_spawns[0]
            try:
                spawns.resume_spawn(paused_spawn.id)
                log.info(f"Resumed paused spawn {paused_spawn.id[:8]} for {identity}")
                continue
            except ValueError as e:
                log.warning(f"Could not resume spawn for {identity}: {e}")

        try:
            log.info(f"Spawning {identity}")
            spawn_ephemeral(identity, instruction=content, channel_id=channel_id)
            log.info(f"Spawned {identity} successfully")
        except Exception as e:
            log.error(f"Spawn error for {identity}: {e}")

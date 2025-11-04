"""Agent spawning: @mentions and task orchestration."""

import logging
import re

from space.os.spawn.api import agents as spawn_agents
from space.os.spawn.api.launch import spawn_headless

log = logging.getLogger(__name__)


def _parse_mentions(content: str) -> list[str]:
    """Extract @identity mentions from content."""
    pattern = r"@([\w-]+)"
    matches = re.findall(pattern, content)
    return list(set(matches))


def spawn_from_mentions(channel_id: str, content: str, agent_id: str | None = None) -> None:
    """Spawn agents from @mentions in message content (async, non-blocking).

    Args:
        channel_id: Channel where message was posted
        content: Message content with potential @mentions
        agent_id: If provided, skip processing mentions from this agent (prevents cascades)
    """
    import threading

    def _spawn_async():
        try:
            from . import channels

            channel = channels.get_channel(channel_id)
            if not channel:
                log.error(f"Channel {channel_id} not found")
                return
            channel_name = channel.name
            _process_mentions(channel_id, channel_name, content, agent_id)
        except Exception as e:
            log.error(f"Failed to spawn from mentions: {e}")

    thread = threading.Thread(target=_spawn_async, daemon=True)
    thread.start()


def _process_mentions(
    channel_id: str, channel_name: str, content: str, sender_agent_id: str | None = None
) -> None:
    """Process @mentions and spawn agents headlessly."""
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
        log.info(f"Spawning {identity}")
        agent = spawn_agents.get_agent(identity)
        if not agent:
            log.warning(f"Identity {identity} not found in registry")
            continue

        try:
            spawn_headless(identity, task=content, channel_id=channel_id)
            log.info(f"Spawned {identity} successfully")
        except Exception as e:
            log.error(f"Spawn error for {identity}: {e}")

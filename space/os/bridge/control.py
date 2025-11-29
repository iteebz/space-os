"""/slash human control commands: /stop, /timer, /compact."""

import logging
import re

from space.core.models import SPAWN_LIVE_STATUSES
from space.os.spawn import agents as spawn_agents
from space.os.spawn import spawns

log = logging.getLogger(__name__)


def process_control_commands(channel_id: str, content: str, agent_id: str | None = None) -> None:
    """Route /slash commands to handlers."""
    if "/timer-cancel" in content:
        _cancel_timer(channel_id)
    elif "/timer" in content:
        _set_timer(channel_id, content)
    elif "/stop-all" in content:
        _stop_all_agents_in_channel(channel_id)
    elif "/stop" in content:
        targets = _extract_control_targets(r"/stop\s+([\w-]+)", content)
        for identity in targets:
            _stop_agent_in_channel(channel_id, identity)

    if "/compact" in content:
        targets = _extract_control_targets(r"/compact\s+([\w-]+)", content)
        for identity in targets:
            _compact_agent_in_channel(channel_id, identity)


def _extract_control_targets(pattern: str, content: str) -> list[str]:
    """Extract identity targets from control command."""
    matches = re.findall(pattern, content)
    return [m for m in matches if m]


def _set_timer(channel_id: str, content: str) -> None:
    """Parse /timer 7d, /timer 8h, or /timer 30m and set channel timer."""
    from datetime import datetime, timedelta

    from . import channels, messaging

    match = re.search(r"/timer\s+(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?", content)
    if not match:
        return

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)

    if days == 0 and hours == 0 and minutes == 0:
        return

    duration = timedelta(days=days, hours=hours, minutes=minutes)
    expires_at = datetime.utcnow() + duration

    channels.set_timer(channel_id, expires_at.isoformat())

    total_minutes = days * 1440 + hours * 60 + minutes
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    duration_str = " ".join(parts)

    messaging.create_message(
        channel_id=channel_id,
        agent_id="system",
        content=f"Timer set: {duration_str} ({total_minutes} minutes)\nChannel will auto-stop at deadline.\nUse /timer-cancel to abort.",
    )
    log.info(f"Timer set for channel {channel_id}: {duration_str}")


def _cancel_timer(channel_id: str) -> None:
    """Cancel active timer for channel."""
    from . import channels, messaging

    channel = channels.get_channel(channel_id)
    if not channel or not channel.timer_expires_at:
        return

    channels.clear_timer(channel_id)
    messaging.create_message(
        channel_id=channel_id,
        agent_id="system",
        content="Timer cancelled.",
    )
    log.info(f"Timer cancelled for channel {channel_id}")


def _stop_all_agents_in_channel(channel_id: str) -> None:
    """Emergency brake: stop all spawns in channel."""
    for spawn in spawns.get_channel_spawns(channel_id):
        if spawn.status in SPAWN_LIVE_STATUSES:
            spawns.terminate_spawn(spawn.id, "killed")
    log.info(f"Stopped all agents in channel {channel_id}")


def _stop_agent_in_channel(channel_id: str, identity: str) -> None:
    """Stop agent in channel."""
    agent = spawn_agents.get_agent(identity)
    if not agent:
        return

    for spawn in spawns.get_spawns_for_agent(agent.agent_id):
        if spawn.channel_id == channel_id and spawn.status in SPAWN_LIVE_STATUSES:
            spawns.terminate_spawn(spawn.id, "killed")


def _compact_agent_in_channel(channel_id: str, identity: str) -> None:
    """Human-initiated agent compaction: force fresh session."""
    from space.lib.detach import detach

    agent = spawn_agents.get_agent(identity)
    if not agent:
        return

    current_spawn = spawns.get_active_spawn_in_channel(agent.agent_id, channel_id)
    if not current_spawn:
        return

    detach(
        [
            "spawn",
            "run",
            agent.identity,
            "Human-initiated compact, continue work",
            "--channel",
            channel_id,
            "--parent-spawn",
            current_spawn.id,
        ]
    )

    spawns.terminate_spawn(current_spawn.id, "completed")

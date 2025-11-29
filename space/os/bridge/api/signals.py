"""!bang agent signals: !compact, !compact-channel, !handoff."""

import logging
import re

from space.core.models import SPAWN_LIVE_STATUSES
from space.os.spawn.api import agents as spawn_agents
from space.os.spawn.api import spawns

log = logging.getLogger(__name__)


def process_signals(channel_id: str, content: str, agent_id: str | None = None) -> None:
    """Route !bang commands to handlers."""
    if "!compact-channel" in content:
        _process_compact_channel(channel_id, content, agent_id)
    elif "!compact" in content:
        _process_compact(channel_id, content, agent_id)

    if "!handoff" in content:
        _process_handoff(channel_id, content, agent_id)


def _get_base_identity(identity: str) -> str:
    """Normalize identity to base form (strip model/constitution suffix)."""
    return identity.split("-")[0]


def _process_compact_channel(channel_id: str, content: str, sender_agent_id: str | None) -> None:
    """Parse !compact-channel summary and create successor channel."""
    from . import channels, messaging

    if not sender_agent_id:
        return

    channel_compact_coordinator = "prime"

    sender_agent = spawn_agents.get_agent(sender_agent_id)
    if not sender_agent:
        return

    sender_base = _get_base_identity(sender_agent.identity)
    coordinator_base = _get_base_identity(channel_compact_coordinator)

    if sender_base != coordinator_base:
        log.info(
            f"{sender_agent.identity} attempted compact, only {channel_compact_coordinator} authorized"
        )
        return

    match = re.search(r"!compact-channel\s+(.+)", content, re.DOTALL)
    if not match:
        return

    summary = match.group(1).strip()
    if not summary:
        return

    current_channel = channels.get_channel(channel_id)
    if not current_channel:
        return

    base_name = current_channel.name
    suffix = 2
    new_name = f"{base_name}-c{suffix}"
    while channels.get_channel(new_name):
        suffix += 1
        new_name = f"{base_name}-c{suffix}"

    new_channel = channels.create_channel(
        name=new_name,
        topic=f"Continuation of {base_name}",
        parent_channel_id=current_channel.channel_id,
    )

    messaging.create_message(
        channel_id=new_channel.channel_id,
        agent_id=sender_agent_id,
        content=f"[CHANNEL COMPACT] Parent: {base_name}\n\nSummary: {summary}",
        metadata={"type": "CHANNEL_COMPACT", "parent_channel_id": current_channel.channel_id},
    )

    agents_in_channel = _get_agents_in_channel(channel_id)
    if agents_in_channel:
        agent_mentions = " ".join([f"@{identity}" for identity in agents_in_channel])
        messaging.create_message(
            channel_id=new_channel.channel_id,
            agent_id=sender_agent_id,
            content=f"{agent_mentions} Channel rotated from {base_name}. Continue work here.",
            metadata={"type": "CHANNEL_MIGRATION"},
        )

    channels.archive_channel(current_channel.name)
    log.info(f"Channel compacted: {base_name} -> {new_name}")


def _get_agents_in_channel(channel_id: str) -> list[str]:
    """Get list of agent identities currently active in channel."""
    active_agents = set()
    for spawn in spawns.get_channel_spawns(channel_id, status=["running", "pending"]):
        agent = spawn_agents.get_agent(spawn.agent_id)
        if agent and agent.identity:
            active_agents.add(agent.identity)
    return list(active_agents)


def _process_compact(channel_id: str, content: str, sender_agent_id: str | None) -> None:
    """Parse !compact summary and spawn successor with parent link."""
    from space.lib.detach import detach

    if not sender_agent_id:
        return

    match = re.search(r"!compact\s+(.+)", content, re.DOTALL)
    if not match:
        return

    summary = match.group(1).strip()
    if not summary:
        return

    sender_agent = spawn_agents.get_agent(sender_agent_id)
    if not sender_agent:
        return

    current_spawn = spawns.get_active_spawn_in_channel(sender_agent_id, channel_id)
    if not current_spawn:
        return

    detach(
        [
            "spawn",
            "run",
            sender_agent.identity,
            "Continue from compact",
            "--channel",
            channel_id,
            "--parent-spawn",
            current_spawn.id,
        ]
    )

    spawns.terminate_spawn(current_spawn.id, "completed")


def _process_handoff(channel_id: str, content: str, sender_agent_id: str | None) -> None:
    """Parse !handoff @target summary and create handoff + spawn target + complete sender."""
    from space.lib.detach import detach

    from . import handoffs

    if not sender_agent_id:
        return

    match = re.search(r"!handoff\s+@([\w-]+)\s+(.+)", content, re.DOTALL)
    if not match:
        return

    target_identity = match.group(1)
    summary = match.group(2).strip()

    sender_agent = spawn_agents.get_agent(sender_agent_id)
    if not sender_agent:
        return

    target_agent = spawn_agents.get_agent(target_identity)
    if not target_agent or not target_agent.model:
        return

    try:
        handoffs.create_handoff(channel_id, sender_agent.identity, target_identity, summary)
    except ValueError as e:
        log.error(f"Failed to create handoff: {e}")
        return

    existing = spawns.get_active_spawn_in_channel(target_agent.agent_id, channel_id)
    if not existing:
        detach(["spawn", "run", target_identity, content, "--channel", channel_id])

    for spawn in spawns.get_spawns_for_agent(sender_agent_id):
        if spawn.channel_id == channel_id and spawn.status in SPAWN_LIVE_STATUSES:
            spawns.terminate_spawn(spawn.id, "completed")

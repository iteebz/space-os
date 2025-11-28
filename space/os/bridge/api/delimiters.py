"""Bridge delimiter parsing: @spawn, !agent-signals, /human-control, #channels."""

import contextlib
import logging
import re

from space.os.spawn.api import agents as spawn_agents
from space.os.spawn.api import spawns

log = logging.getLogger(__name__)


def _extract_mentions(content: str) -> list[str]:
    return list(set(re.findall(r"@([\w-]+)", content)))


def _extract_control_targets(pattern: str, content: str) -> list[str]:
    """Extract identity targets from control command. Empty list means 'all'."""
    matches = re.findall(pattern, content)
    return [m for m in matches if m]


async def process_delimiters(channel_id: str, content: str, agent_id: str | None = None) -> None:
    """Fire-and-forget: parse @mentions and !control commands."""
    from . import channels

    channel = channels.get_channel(channel_id)
    if not channel:
        log.error(f"Channel {channel_id} not found")
        return

    try:
        _process_control_commands(channel_id, content, agent_id)
        _process_mentions(channel_id, content, agent_id)
    except Exception as e:
        log.error(f"Failed to process delimiters: {e}", exc_info=True)


def _process_control_commands(channel_id: str, content: str, agent_id: str | None = None) -> None:
    # Human control surface: /slash commands
    if "/pause" in content:
        targets = _extract_control_targets(r"/pause(?:\s+([\w-]+))?", content)
        if not targets:
            _pause_all_in_channel(channel_id)
        else:
            for identity in targets:
                _pause_agent_in_channel(channel_id, identity)

    if "/resume" in content:
        targets = _extract_control_targets(r"/resume(?:\s+([\w-]+))?", content)
        if not targets:
            _resume_all_in_channel(channel_id)
        else:
            for identity in targets:
                _resume_agent_in_channel(channel_id, identity)

    if "/abort" in content:
        targets = _extract_control_targets(r"/abort(?:\s+([\w-]+))?", content)
        if not targets:
            _abort_all_in_channel(channel_id)
        else:
            for identity in targets:
                _abort_agent_in_channel(channel_id, identity)

    if "/compact" in content:
        targets = _extract_control_targets(r"/compact(?:\s+([\w-]+))?", content)
        for identity in targets:
            _compact_agent_in_channel(channel_id, identity)

    # Agent signal surface: !bang commands
    if "!compact-channel" in content:
        _process_compact_channel_command(channel_id, content, agent_id)
    elif "!compact" in content:
        _process_compact_command(channel_id, content, agent_id)

    if "!handoff" in content:
        _process_handoff_command(channel_id, content, agent_id)


def _pause_all_in_channel(channel_id: str) -> None:
    for spawn in spawns.get_channel_spawns(channel_id, status="running"):
        with contextlib.suppress(ValueError):
            spawns.pause_spawn(spawn.id)


def _pause_agent_in_channel(channel_id: str, identity: str) -> None:
    agent = spawn_agents.get_agent(identity)
    if not agent:
        return
    for spawn in spawns.get_spawns_for_agent(agent.agent_id):
        if spawn.status == "running" and spawn.channel_id == channel_id:
            with contextlib.suppress(ValueError):
                spawns.pause_spawn(spawn.id)


def _resume_all_in_channel(channel_id: str) -> None:
    for spawn in spawns.get_channel_spawns(channel_id, status="paused"):
        with contextlib.suppress(ValueError):
            spawns.resume_spawn(spawn.id)


def _resume_agent_in_channel(channel_id: str, identity: str) -> None:
    agent = spawn_agents.get_agent(identity)
    if not agent:
        return
    for spawn in spawns.get_spawns_for_agent(agent.agent_id):
        if spawn.status == "paused" and spawn.channel_id == channel_id:
            with contextlib.suppress(ValueError):
                spawns.resume_spawn(spawn.id)


def _abort_all_in_channel(channel_id: str) -> None:
    for spawn in spawns.get_channel_spawns(channel_id, status="running"):
        _kill_spawn(spawn.id)


def _abort_agent_in_channel(channel_id: str, identity: str) -> None:
    agent = spawn_agents.get_agent(identity)
    if not agent:
        return
    for spawn in spawns.get_spawns_for_agent(agent.agent_id):
        if spawn.status == "running" and spawn.channel_id == channel_id:
            _kill_spawn(spawn.id)


def _kill_spawn(spawn_id: str) -> None:
    import os
    import signal
    import time

    spawn = spawns.get_spawn(spawn_id)
    if spawn and spawn.pid:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(spawn.pid, signal.SIGTERM)
        time.sleep(0.5)
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(spawn.pid, signal.SIGKILL)
    spawns.update_status(spawn_id, "killed")


def _process_mentions(channel_id: str, content: str, sender_agent_id: str | None = None) -> None:
    from space.lib.detach import detach

    mentions = _extract_mentions(content)
    if not mentions:
        return

    for identity in mentions:
        agent = spawn_agents.get_agent(identity)
        if not agent or agent.agent_id == sender_agent_id:
            continue
        if not agent.model:
            continue

        if _try_resume_paused_spawn(agent.agent_id, channel_id):
            continue

        if _has_running_spawn_in_channel(agent.agent_id, channel_id):
            continue

        detach(["spawn", "run", identity, content, "--channel", channel_id])


def _attempt_relink_for_agent(agent_id: str) -> None:
    """Try to discover and link session_id for recent unlinked spawns."""
    from space.lib import store
    from space.os.spawn.api.launch import _discover_recent_session

    agent = spawn_agents.get_agent(agent_id)
    if not agent or not agent.model:
        return

    provider = agent.model.split("-")[0] if agent.model else None
    if provider not in ("claude", "codex", "gemini"):
        return

    with store.ensure() as conn:
        unlinked = conn.execute(
            """SELECT id, created_at FROM spawns
            WHERE agent_id = ? AND session_id IS NULL AND status = 'completed'
            ORDER BY created_at DESC LIMIT 5""",
            (agent_id,),
        ).fetchall()

    for row in unlinked:
        spawn_id, created_at = row
        session_id = _discover_recent_session(provider, created_at)
        if session_id:
            spawns.link_session_to_spawn(spawn_id, session_id)
            log.info(f"Relinked spawn {spawn_id[:12]} -> session {session_id[:12]}")


def _has_running_spawn_in_channel(agent_id: str, channel_id: str) -> bool:
    """Check if agent has running or pending spawn in channel."""
    all_spawns = spawns.get_spawns_for_agent(agent_id)

    for spawn in all_spawns:
        if spawn.channel_id != channel_id:
            continue

        if spawn.status in ("running", "pending"):
            return True

    return False


def _get_base_identity(identity: str) -> str:
    """Normalize identity to base form (strip model/constitution suffix)."""
    return identity.split("-")[0]


def _process_compact_channel_command(
    channel_id: str, content: str, sender_agent_id: str | None
) -> None:
    """Parse !compact-channel summary and create successor channel.

    TODO: Channel compaction hidden from agents (not in prompt) pending raid data.
    - Math: 8h raid ≈ 260 messages, threshold is 500
    - May not need channel compaction for current raid scope
    - Test manually during lunch, evaluate post-raid
    - If needed: add coordinator designation, migration protocol
    """
    from . import channels, messaging

    if not sender_agent_id:
        return

    # COORDINATOR CHECK - only designated agent can compact
    # TODO: Make configurable per channel (human designates at creation)
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

    # Pattern: !compact-channel rest-of-message
    match = re.search(r"!compact-channel\s+(.+)", content, re.DOTALL)
    if not match:
        return

    summary = match.group(1).strip()
    if not summary:
        return

    # Get current channel
    current_channel = channels.get_channel(channel_id)
    if not current_channel:
        return

    # Generate new channel name with suffix
    base_name = current_channel.name
    # Find next available suffix (c2, c3, c4, etc.)
    suffix = 2
    new_name = f"{base_name}-c{suffix}"
    while channels.get_channel(new_name):
        suffix += 1
        new_name = f"{base_name}-c{suffix}"

    # Create successor channel with parent link
    new_channel = channels.create_channel(
        name=new_name,
        topic=f"Continuation of {base_name}",
        parent_channel_id=current_channel.channel_id,
    )

    # Post summary as first message in new channel
    messaging.create_message(
        channel_id=new_channel.channel_id,
        agent_id=sender_agent_id,
        content=f"[CHANNEL COMPACT] Parent: {base_name}\n\nSummary: {summary}",
        metadata={"type": "CHANNEL_COMPACT", "parent_channel_id": current_channel.channel_id},
    )

    # Get all agents currently in old channel and @mention them in new channel
    # This triggers automatic spawning via mention detection
    agents_in_channel = _get_agents_in_channel(channel_id)
    if agents_in_channel:
        agent_mentions = " ".join([f"@{identity}" for identity in agents_in_channel])
        messaging.create_message(
            channel_id=new_channel.channel_id,
            agent_id=sender_agent_id,
            content=f"{agent_mentions} Channel rotated from {base_name}. Continue work here.",
            metadata={"type": "CHANNEL_MIGRATION"},
        )

    # Archive old channel
    channels.archive_channel(current_channel.name)

    log.info(f"Channel compacted: {base_name} → {new_name}")


def _get_agents_in_channel(channel_id: str) -> list[str]:
    """Get list of agent identities currently active in channel."""
    from space.os.spawn.api import agents as spawn_agents

    active_agents = set()
    for spawn in spawns.get_channel_spawns(channel_id, status=["running", "pending"]):
        agent = spawn_agents.get_agent(spawn.agent_id)
        if agent and agent.identity:
            active_agents.add(agent.identity)

    return list(active_agents)


def _compact_agent_in_channel(channel_id: str, identity: str) -> None:
    """Human-initiated agent compaction: force fresh session."""
    from space.lib.detach import detach

    agent = spawn_agents.get_agent(identity)
    if not agent:
        return

    # Find running spawn in channel
    current_spawn = None
    for spawn in spawns.get_spawns_for_agent(agent.agent_id):
        if spawn.status == "running" and spawn.channel_id == channel_id:
            current_spawn = spawn
            break

    if not current_spawn:
        return

    # Spawn successor with parent link
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

    # Kill current spawn
    _kill_spawn(current_spawn.id)


def _process_compact_command(channel_id: str, content: str, sender_agent_id: str | None) -> None:
    """Parse !compact summary and spawn successor with parent link."""
    from space.lib.detach import detach

    if not sender_agent_id:
        return

    # Pattern: !compact rest-of-message
    match = re.search(r"!compact\s+(.+)", content, re.DOTALL)
    if not match:
        return

    summary = match.group(1).strip()
    if not summary:
        return

    sender_agent = spawn_agents.get_agent(sender_agent_id)
    if not sender_agent:
        return

    # Get current spawn in this channel
    current_spawn = None
    for spawn in spawns.get_spawns_for_agent(sender_agent_id):
        if spawn.status == "running" and spawn.channel_id == channel_id:
            current_spawn = spawn
            break

    if not current_spawn:
        return

    # Spawn successor with parent link (compact message already in channel transcript)
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

    # Kill current spawn
    _kill_spawn(current_spawn.id)


def _process_handoff_command(channel_id: str, content: str, sender_agent_id: str | None) -> None:
    """Parse !handoff @target summary and create handoff + spawn target + kill sender."""
    from space.lib.detach import detach

    from . import handoffs

    if not sender_agent_id:
        return

    # Pattern: !handoff @target rest-of-message
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

    # Create handoff record
    try:
        handoffs.create_handoff(channel_id, sender_agent.identity, target_identity, summary)
    except ValueError as e:
        log.error(f"Failed to create handoff: {e}")
        return

    # Spawn target agent if not already running
    if not _has_running_spawn_in_channel(target_agent.agent_id, channel_id):
        detach(["spawn", "run", target_identity, content, "--channel", channel_id])

    # Kill sender's spawn in this channel
    for spawn in spawns.get_spawns_for_agent(sender_agent_id):
        if spawn.status == "running" and spawn.channel_id == channel_id:
            _kill_spawn(spawn.id)


def _try_resume_paused_spawn(agent_id: str, channel_id: str | None = None) -> bool:
    """Resume the most relevant paused spawn for agent (prefer same channel)."""
    paused = spawns.get_spawns_for_agent(agent_id, status="paused")
    if not paused:
        return False

    attempted_ids: set[str] = set()

    def _resume(candidates: list) -> bool:
        for spawn in candidates:
            if spawn.id in attempted_ids:
                continue
            attempted_ids.add(spawn.id)
            try:
                spawns.resume_spawn(spawn.id)
                return True
            except ValueError:
                continue
        return False

    if channel_id:
        channel_matches = [spawn for spawn in paused if spawn.channel_id == channel_id]
        if _resume(channel_matches):
            return True

    return _resume(paused)

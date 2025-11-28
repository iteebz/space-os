"""Bridge delimiter parsing: @spawn, !agent-signals, /human-control, #channels."""

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

    # Agent signal surface: !bang commands
    if "!compact-channel" in content:
        _process_compact_channel_command(channel_id, content, agent_id)
    elif "!compact" in content:
        _process_compact_command(channel_id, content, agent_id)

    if "!handoff" in content:
        _process_handoff_command(channel_id, content, agent_id)


def _set_timer(channel_id: str, content: str) -> None:
    """Parse /timer 7d, /timer 8h, or /timer 30m and set channel timer."""
    import re
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
        content=f"⏱️ Timer set: {duration_str} ({total_minutes} minutes)\nChannel will auto-stop at deadline.\nUse /timer-cancel to abort.",
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
        content="⏱️ Timer cancelled.",
    )
    log.info(f"Timer cancelled for channel {channel_id}")


def _stop_all_agents_in_channel(channel_id: str) -> None:
    """Emergency brake: kill all active spawns in channel."""
    from space.core.models import SpawnStatus

    active_statuses = {SpawnStatus.RUNNING, SpawnStatus.PENDING}
    for spawn in spawns.get_channel_spawns(channel_id):
        if spawn.status in active_statuses:
            _kill_spawn(spawn.id)
    log.info(f"Killed all agents in channel {channel_id}")


def _stop_agent_in_channel(channel_id: str, identity: str) -> None:
    """Stop agent in channel (kill all active spawns)."""
    from space.core.models import SpawnStatus

    agent = spawn_agents.get_agent(identity)
    if not agent:
        return

    active_statuses = {SpawnStatus.RUNNING, SpawnStatus.PENDING}
    for spawn in spawns.get_spawns_for_agent(agent.agent_id):
        if spawn.status in active_statuses and spawn.channel_id == channel_id:
            _kill_spawn(spawn.id)


def _kill_spawn(spawn_id: str) -> None:
    """Kill spawn process with SIGTERM → SIGKILL escalation."""
    import os
    import signal
    import time

    spawn = spawns.get_spawn(spawn_id)
    if not spawn:
        log.warning(f"Cannot kill spawn {spawn_id}: not found")
        return

    if not spawn.pid:
        log.warning(f"Cannot kill spawn {spawn_id}: no PID (process never started)")
        spawns.update_status(spawn_id, "killed")
        return

    # Try graceful shutdown first
    try:
        os.kill(spawn.pid, signal.SIGTERM)
    except ProcessLookupError:
        log.debug(f"Spawn {spawn_id} already dead (SIGTERM)")
        spawns.update_status(spawn_id, "killed")
        return
    except OSError as e:
        log.error(f"Failed to send SIGTERM to spawn {spawn_id} PID {spawn.pid}: {e}")
        spawns.update_status(spawn_id, "killed")
        return

    # Poll for up to 5s to see if process exits cleanly
    for _ in range(10):
        time.sleep(0.5)
        try:
            os.kill(spawn.pid, 0)  # Check if alive
        except ProcessLookupError:
            log.debug(f"Spawn {spawn_id} exited cleanly after SIGTERM")
            spawns.update_status(spawn_id, "killed")
            return

    # Still alive, force kill
    try:
        os.kill(spawn.pid, signal.SIGKILL)
        log.info(f"Spawn {spawn_id} required SIGKILL")
    except ProcessLookupError:
        log.debug(f"Spawn {spawn_id} died during SIGKILL window")
    except OSError as e:
        log.error(f"Failed to send SIGKILL to spawn {spawn_id} PID {spawn.pid}: {e}")

    spawns.update_status(spawn_id, "killed")


def _get_last_session_in_channel(agent_id: str, channel_id: str) -> str | None:
    """Get most recent session for agent in channel.

    Returns None if no previous spawns or if last spawn has no session_id.
    """
    channel_spawns = spawns.get_channel_spawns(channel_id, agent_id=agent_id, limit=1)
    if channel_spawns and channel_spawns[0].session_id:
        return channel_spawns[0].session_id
    return None


def _process_mentions(channel_id: str, content: str, sender_agent_id: str | None = None) -> None:
    """Process @mentions: spawn agent if not already running in channel.

    Session continuity: @mention resumes last session in channel if one exists.
    """
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

        if _has_running_spawn_in_channel(agent.agent_id, channel_id):
            continue

        cmd = ["spawn", "run", identity, content, "--channel", channel_id]

        last_session = _get_last_session_in_channel(agent.agent_id, channel_id)
        if last_session:
            cmd.extend(["--resume", last_session])

        detach(cmd)


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
    from space.core.models import SpawnStatus

    all_spawns = spawns.get_spawns_for_agent(agent_id)

    for spawn in all_spawns:
        if spawn.channel_id != channel_id:
            continue

        if spawn.status in (SpawnStatus.RUNNING, SpawnStatus.PENDING):
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
    from space.core.models import SpawnStatus
    from space.lib.detach import detach

    agent = spawn_agents.get_agent(identity)
    if not agent:
        return

    # Find running spawn in channel
    current_spawn = None
    for spawn in spawns.get_spawns_for_agent(agent.agent_id):
        if spawn.status == SpawnStatus.RUNNING and spawn.channel_id == channel_id:
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
    from space.core.models import SpawnStatus
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
        if spawn.status == SpawnStatus.RUNNING and spawn.channel_id == channel_id:
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
    from space.core.models import SpawnStatus
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
        if spawn.status == SpawnStatus.RUNNING and spawn.channel_id == channel_id:
            _kill_spawn(spawn.id)

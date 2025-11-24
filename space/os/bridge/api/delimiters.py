"""Bridge delimiter parsing: @spawn, !control, #channels, /docs."""

import contextlib
import logging
import re

from space.os.spawn.api import agents as spawn_agents
from space.os.spawn.api import spawns
from space.os.spawn.api.launch import spawn_ephemeral

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
        _process_control_commands(channel_id, content)
        _process_mentions(channel_id, content, agent_id)
    except Exception as e:
        log.error(f"Failed to process delimiters: {e}", exc_info=True)


def _process_control_commands(channel_id: str, content: str) -> None:
    if "!pause" in content:
        targets = _extract_control_targets(r"!pause(?:\s+([\w-]+))?", content)
        if not targets:
            _pause_all_in_channel(channel_id)
        else:
            for identity in targets:
                _pause_agent_in_channel(channel_id, identity)

    if "!resume" in content:
        targets = _extract_control_targets(r"!resume(?:\s+([\w-]+))?", content)
        if not targets:
            _resume_all_in_channel(channel_id)
        else:
            for identity in targets:
                _resume_agent_in_channel(channel_id, identity)

    if "!abort" in content:
        targets = _extract_control_targets(r"!abort(?:\s+([\w-]+))?", content)
        if not targets:
            _abort_all_in_channel(channel_id)
        else:
            for identity in targets:
                _abort_agent_in_channel(channel_id, identity)


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

    spawn = spawns.get_spawn(spawn_id)
    if spawn and spawn.pid:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(spawn.pid, signal.SIGTERM)
    spawns.update_status(spawn_id, "killed")


def _process_mentions(channel_id: str, content: str, sender_agent_id: str | None = None) -> None:
    mentions = _extract_mentions(content)
    if not mentions:
        return

    for identity in mentions:
        agent = spawn_agents.get_agent(identity)
        if not agent or agent.agent_id == sender_agent_id:
            continue
        if not agent.model:
            continue

        if _try_resume_paused_spawn(agent.agent_id):
            continue

        _spawn_agent(identity, content, channel_id)


def _attempt_relink_for_agent(agent_id: str) -> None:
    """Try to discover and link session_id for recent unlinked spawns."""
    from space.lib import store
    from space.os.spawn.api.launch import _discover_recent_session
    
    agent = spawn_agents.get_agent(agent_id)
    if not agent or not agent.model:
        return
    
    provider = agent.model.split('-')[0] if agent.model else None
    if provider not in ('claude', 'codex', 'gemini'):
        return
    
    with store.ensure() as conn:
        unlinked = conn.execute(
            """SELECT id, created_at FROM spawns 
            WHERE agent_id = ? AND session_id IS NULL AND status = 'completed'
            ORDER BY created_at DESC LIMIT 5""",
            (agent_id,)
        ).fetchall()
    
    for row in unlinked:
        spawn_id, created_at = row
        session_id = _discover_recent_session(provider, created_at)
        if session_id:
            spawns.link_session_to_spawn(spawn_id, session_id)
            log.info(f"Relinked spawn {spawn_id[:12]} -> session {session_id[:12]}")


def _try_resume_paused_spawn(agent_id: str) -> bool:
    paused = spawns.get_spawns_for_agent(agent_id, status="paused")
    if not paused:
        return False

    most_recent = max(paused, key=lambda s: s.created_at or "")
    try:
        spawns.resume_spawn(most_recent.id)
        return True
    except ValueError:
        return False


def _spawn_agent(identity: str, instruction: str, channel_id: str) -> None:
    try:
        agent = spawn_agents.get_agent(identity)
        if agent:
            _attempt_relink_for_agent(agent.agent_id)
        spawn_ephemeral(identity, instruction=instruction, channel_id=channel_id)
    except Exception as e:
        log.error(f"Failed to spawn {identity}: {e}")

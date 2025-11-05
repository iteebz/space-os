"""Bridge delimiter parsing: @spawn, !control, #channels, /docs."""

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


def _parse_control_commands(content: str) -> dict[str, list[str]]:
    """Extract !command [identity] control directives from content.

    Supports:
    - !pause [identity]  (pause specific or all if bare)
    - !resume [identity] (resume specific or all if bare)
    - !identity          (backward compat: implies pause)

    Returns dict with keys: pause, resume
    Each value is list of identities (empty list if bare command, i.e., pause/resume all)
    """
    # New explicit syntax: !pause [identity] or !resume [identity]
    pause_pattern = r"!pause(?:\s+([\w-]+))?"
    resume_pattern = r"!resume(?:\s+([\w-]+))?"

    pause_matches = re.findall(pause_pattern, content)
    resume_matches = re.findall(resume_pattern, content)

    # Backward compat: bare !identity (no command) = pause
    bare_identity_pattern = r"!(?!pause|resume)([\w-]+)"
    bare_identities = re.findall(bare_identity_pattern, content)

    # pause_matches may contain empty strings for bare !pause, filter those
    pause_identities = [m for m in pause_matches if m]
    resume_identities = [m for m in resume_matches if m]

    # Check for bare !pause or !resume (no identity)
    has_bare_pause = bool(re.search(r"!pause(?:\s|$|[^\w-])", content))
    has_bare_resume = bool(re.search(r"!resume(?:\s|$|[^\w-])", content))

    # Combine: explicit + backward compat
    all_pause_identities = pause_identities + bare_identities

    return {
        "pause": all_pause_identities if all_pause_identities or has_bare_pause else [],
        "resume": resume_identities if resume_identities or has_bare_resume else [],
    }


def spawn_from_mentions(channel_id: str, content: str, agent_id: str | None = None) -> None:
    """Process delimiters from message content (async, non-blocking).

    Args:
        channel_id: Channel where message was posted
        content: Message content with potential @mentions and !control commands
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
            _process_control_commands_impl(channel_id, content)
            _process_mentions(channel_id, content, agent_id)
        except Exception as e:
            log.error(f"Failed to process delimiters: {e}")

    thread = threading.Thread(target=_process_async, daemon=True)
    thread.start()


def _process_control_commands_impl(channel_id: str, content: str) -> None:
    """Process !pause and !resume control directives."""
    commands = _parse_control_commands(content)

    # Handle pause commands
    if commands["pause"]:
        pause_identities = commands["pause"] if commands["pause"][0] else None
        _handle_pause(pause_identities, channel_id)

    # Handle resume commands
    if commands["resume"]:
        resume_identities = commands["resume"] if commands["resume"][0] else None
        _handle_resume(resume_identities, channel_id)


def _handle_pause(identities: list[str] | None, channel_id: str) -> None:
    """Pause running spawns for given identities, optionally scoped to channel.

    If identities is None/empty (bare !pause), pauses all running spawns in channel.
    If identities are specified (!pause identity), pauses all running spawns for that identity.
    """
    if identities is None or (isinstance(identities, list) and not identities):
        # Bare !pause: pause all running spawns in this channel
        log.info(f"Pausing all running spawns in channel {channel_id}")
        all_running = spawns.get_channel_spawns(channel_id, status="running")
        for spawn_obj in all_running:
            try:
                spawns.pause_spawn(spawn_obj.id)
                log.info(f"Paused spawn {spawn_obj.id[:8]}")
            except ValueError as e:
                log.warning(f"Could not pause spawn {spawn_obj.id[:8]}: {e}")
        return

    for identity in identities:
        log.info(f"Pausing {identity}")
        agent = spawn_agents.get_agent(identity)
        if not agent:
            log.warning(f"Identity {identity} not found in registry")
            continue

        # !pause identity: pause all running spawns for that identity (any channel)
        running_spawns = [
            s for s in spawns.get_spawns_for_agent(agent.agent_id) if s.status == "running"
        ]
        if not running_spawns:
            log.info(f"No running spawns for {identity}")
            continue

        for spawn_obj in running_spawns:
            try:
                spawns.pause_spawn(spawn_obj.id)
                log.info(f"Paused spawn {spawn_obj.id[:8]} for {identity}")
            except ValueError as e:
                log.warning(f"Could not pause {identity}: {e}")


def _handle_resume(identities: list[str] | None, channel_id: str) -> None:
    """Resume paused spawns for given identities, optionally scoped to channel.

    If identities is None/empty (bare !resume), resumes all paused spawns in channel.
    If identities are specified (!resume identity), resumes all paused spawns for that identity.
    """
    if identities is None or (isinstance(identities, list) and not identities):
        # Bare !resume: resume all paused spawns in this channel
        log.info(f"Resuming all paused spawns in channel {channel_id}")
        all_paused = spawns.get_channel_spawns(channel_id, status="paused")
        for spawn_obj in all_paused:
            try:
                spawns.resume_spawn(spawn_obj.id)
                log.info(f"Resumed spawn {spawn_obj.id[:8]}")
            except ValueError as e:
                log.warning(f"Could not resume spawn {spawn_obj.id[:8]}: {e}")
        return

    for identity in identities:
        log.info(f"Resuming {identity}")
        agent = spawn_agents.get_agent(identity)
        if not agent:
            log.warning(f"Identity {identity} not found in registry")
            continue

        # !resume identity: resume all paused spawns for that identity (any channel)
        paused_spawns = [
            s for s in spawns.get_spawns_for_agent(agent.agent_id) if s.status == "paused"
        ]
        if not paused_spawns:
            log.info(f"No paused spawns for {identity}")
            continue

        for spawn_obj in paused_spawns:
            try:
                spawns.resume_spawn(spawn_obj.id)
                log.info(f"Resumed spawn {spawn_obj.id[:8]} for {identity}")
            except ValueError as e:
                log.warning(f"Could not resume {identity}: {e}")


def _process_mentions(channel_id: str, content: str, sender_agent_id: str | None = None) -> None:
    """Process @mentions: check for paused spawns first, then spawn or resume."""
    log.info(f"Processing channel={channel_id}, content={content[:50]}")

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

"""@mention processing: spawn agents on @identity."""

import logging
import re

from space.os.spawn import agents as spawn_agents
from space.os.spawn import spawns

log = logging.getLogger(__name__)


def extract_mentions(content: str) -> list[str]:
    return list(set(re.findall(r"@([\w-]+)", content)))


def process_mentions(channel_id: str, content: str, sender_agent_id: str | None = None) -> None:
    """Process @mentions: reuse active spawn or create new one.

    Spawn lifecycle:
    - First @mention: create spawn, CLI runs, spawn becomes ACTIVE
    - Subsequent @mentions: reuse ACTIVE spawn, CLI runs, spawn stays ACTIVE
    - !compact/!handoff: spawn COMPLETED, successor created
    """
    from space.lib.detach import detach

    mentions = extract_mentions(content)
    if not mentions:
        return

    for identity in mentions:
        agent = spawn_agents.get_agent(identity)
        if not agent or agent.agent_id == sender_agent_id:
            continue
        if not agent.model:
            continue

        existing_spawn = spawns.get_active_spawn_in_channel(agent.agent_id, channel_id)

        if existing_spawn and existing_spawn.status == "running":
            continue

        if existing_spawn and existing_spawn.status == "active":
            cmd = [
                "spawn",
                "run",
                identity,
                content,
                "--channel",
                channel_id,
                "--spawn-id",
                existing_spawn.id,
            ]
            if existing_spawn.session_id:
                cmd.extend(["--resume", existing_spawn.session_id])
            detach(cmd)
        else:
            cmd = ["spawn", "run", identity, content, "--channel", channel_id]
            detach(cmd)


def attempt_relink_for_agent(agent_id: str) -> None:
    """Try to discover and link session_id for recent unlinked spawns."""
    from space.lib import store
    from space.os.spawn.launch import _discover_recent_session

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

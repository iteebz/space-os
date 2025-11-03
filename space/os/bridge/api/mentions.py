"""Agent spawning: @mentions and task orchestration."""

import logging
import re

from space.lib import paths
from space.os.spawn.api import agents as spawn_agents
from space.os.spawn.api.launch import spawn_agent
from space.os.spawn.api.tasks import complete_task, create_task, fail_task, start_task

log = logging.getLogger(__name__)

AGENT_PROMPT_TEMPLATE = """{context}

[SPACE INSTRUCTIONS]
{task}

Infer the actual task from bridge context. If ambiguous, ask for clarification."""


def _write_role_file(provider: str, constitution: str) -> None:
    """Write pure constitution to agent home dir file."""
    filename_map = {
        "claude": "CLAUDE.md",
        "gemini": "GEMINI.md",
        "codex": "AGENTS.md",
    }
    agent_dir_map = {
        "claude": ".claude",
        "gemini": ".gemini",
        "codex": ".codex",
    }
    filename = filename_map.get(provider)
    agent_dir = agent_dir_map.get(provider)
    if not filename or not agent_dir:
        raise ValueError(f"Unknown provider: {provider}")

    target = Path.home() / agent_dir / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(constitution)


def _parse_mentions(content: str) -> list[str]:
    """Extract @identity mentions from content."""
    pattern = r"@([\w-]+)"
    matches = re.findall(pattern, content)
    return list(set(matches))


def _build_prompt(identity: str, channel: str, content: str) -> str | None:
    """Build agent prompt with task instruction."""
    try:
        agent = spawn_agents.get_agent(identity)
        if not agent:
            log.warning(f"Identity {identity} not found in registry")
            return None

        if agent.constitution:
            const_path = paths.constitution(agent.constitution)
            constitution = const_path.read_text()
            _write_role_file(agent.provider, constitution)

        return AGENT_PROMPT_TEMPLATE.format(context="", task=content)
    except Exception as e:
        log.error(f"Building prompt for {identity} failed: {e}", exc_info=True)
        return None


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
    """Process @mentions and spawn agents inline."""
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
        prompt = _build_prompt(identity, channel_name, content)
        if prompt:
            task_id = create_task(identity=identity, input=prompt, channel_id=channel_id)
            start_task(task_id)
            try:
                spawn_agent(identity, extra_args=[prompt])
                complete_task(task_id, output="Agent completed task")
                log.info(f"Spawned {identity} successfully")
            except Exception as e:
                fail_task(task_id, stderr=str(e))
                log.error(f"Spawn error for {identity}: {e}")
        else:
            log.warning(f"No prompt for {identity}")

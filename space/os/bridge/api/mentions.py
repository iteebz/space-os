"""Agent spawning: @mentions and task orchestration."""

import logging
import re
import subprocess
import sys
from pathlib import Path

from space.lib import paths
from space.os.spawn.api import agents as spawn_agents
from space.os.spawn.api.prompt import spawn_prompt
from space.os.spawn.api.tasks import complete_task, create_task, fail_task, start_task

logging.basicConfig(level=logging.DEBUG, format="[worker] %(message)s")
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
    """Build agent prompt with channel context and task, write constitution."""
    try:
        agent = spawn_agents.get_agent(identity)
        if not agent:
            log.warning(f"Identity {identity} not found in registry")
            return None

        const_path = paths.constitution(agent.constitution)
        constitution = const_path.read_text()

        _write_role_file(agent.provider, constitution)

        identity_prompt = spawn_prompt(identity, agent.model)

        export = subprocess.run(
            ["bridge", "export", channel],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if export.returncode != 0:
            log.error(
                f"bridge export failed for {channel}: "
                f"returncode={export.returncode}, stderr={export.stderr[:200]}"
            )
            return None
        return (
            identity_prompt
            + "\n\n"
            + AGENT_PROMPT_TEMPLATE.format(context=export.stdout, task=content)
        )
    except subprocess.TimeoutExpired:
        log.error(f"bridge export timed out for {channel}")
        return None
    except Exception as e:
        log.error(f"Building prompt for {identity} failed: {e}", exc_info=True)
        return None


def _get_task_timeout(identity: str) -> int:
    """Get task timeout for identity. Uses default since config is gone."""
    return 120


def spawn_from_mentions(channel_id: str, content: str) -> None:
    """Spawn agents from @mentions in message content."""
    try:
        from . import channels

        channel = channels.get_channel(channel_id)
        if not channel:
            log.error(f"Channel {channel_id} not found")
            return
        channel_name = channel.name
        subprocess.run(
            [sys.executable, "-m", "space.os.bridge.api.mentions", channel_id, channel_name, content],
            check=False,
        )
    except Exception as e:
        log.error(f"Failed to spawn from mentions: {e}")


def main():
    if len(sys.argv) != 4:
        log.error(f"Invalid args: {len(sys.argv)}, expected 4. argv={sys.argv}")
        return

    channel_id = sys.argv[1]
    channel_name = sys.argv[2]
    content = sys.argv[3]

    log.info(f"Processing channel={channel_name}, content={content[:50]}")

    mentions = _parse_mentions(content)
    log.info(f"Found mentions: {mentions}")
    if not mentions:
        log.info("No mentions, skipping")
        return

    results = []
    for identity in mentions:
        log.info(f"Spawning {identity}")
        prompt = _build_prompt(identity, channel_name, content)
        if prompt:
            log.info(f"Got prompt, running spawn {identity}")
            timeout = _get_task_timeout(identity)
            try:
                task_id = create_task(identity=identity, input=prompt, channel_id=channel_id)
                start_task(task_id)

                result = subprocess.run(
                    ["spawn", identity, prompt, "--channel", channel_name],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL,
                )

                log.info(
                    f"Spawn returncode={result.returncode}, stdout_len={len(result.stdout)}, stderr={result.stderr[:100]}"
                )

                if result.returncode == 0 and result.stdout.strip():
                    complete_task(
                        task_id,
                        output=result.stdout.strip(),
                    )
                    results.append((identity, result.stdout.strip()))
                else:
                    fail_task(task_id, stderr=result.stderr)
                    log.error(f"Spawn failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                fail_task(
                    task_id,
                    stderr=f"Spawn timeout ({timeout}s)",
                )
                log.error(f"Spawn timeout for {identity}")
            except Exception as e:
                fail_task(task_id, stderr=str(e))
                log.error(f"Spawn error: {e}")
        else:
            log.warning(f"No prompt for {identity}")

    if results:
        from . import messaging

        for identity, output in results:
            messaging.send_message(channel_id, identity, output)
    elif mentions:
        log.warning(f"No results from spawning {len(mentions)} agent(s))")


if __name__ == "__main__":
    main()

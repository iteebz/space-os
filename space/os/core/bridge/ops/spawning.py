"""Agent spawning: @mentions, polls, and task orchestration."""

import logging
import re
import subprocess
import sys

from space.os import config
from space.os.core import spawn
from space.os.models import TaskStatus

logging.basicConfig(level=logging.DEBUG, format="[worker] %(message)s")
log = logging.getLogger(__name__)

AGENT_PROMPT_TEMPLATE = """{context}

[SPACE INSTRUCTIONS]
{task}

Infer the actual task from bridge context. If ambiguous, ask for clarification."""


def _parse_mentions(content: str) -> list[str]:
    """Extract @identity mentions from content."""
    pattern = r"@([\w-]+)"
    matches = re.findall(pattern, content)
    return list(set(matches))


def _parse_poll_command(content: str) -> tuple[str, list[str]]:
    """Extract /poll @agent mentions. Returns (cmd_type, agents)."""
    if content.startswith("/poll "):
        agents = re.findall(r"@([\w-]+)", content[6:])
        return ("poll", list(set(agents)))
    return ("none", [])


def _parse_dismiss_command(content: str) -> tuple[str, list[str]]:
    """Extract !agent dismissals. Returns (cmd_type, agents)."""
    if content.startswith("!"):
        agents = re.findall(r"^!([\w-]+)\s*", content)
        return ("dismiss", agents)
    return ("none", [])


def _extract_mention_task(identity: str, content: str) -> str:
    """Extract task following @identity mention."""
    pattern = rf"@{re.escape(identity)}\s+(.*?)(?=@|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def _build_prompt(identity: str, channel: str, content: str) -> str | None:
    """Build agent prompt with channel context and task."""
    cfg = config.load_config()
    if identity not in cfg.get("roles", {}):
        log.warning(f"Identity {identity} not in config roles")
        return None

    try:
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
        task = _extract_mention_task(identity, content)
        return AGENT_PROMPT_TEMPLATE.format(context=export.stdout, task=task)
    except subprocess.TimeoutExpired:
        log.error(f"bridge export timed out for {channel}")
        return None
    except Exception as e:
        log.error(f"Building prompt for {identity} failed: {e}", exc_info=True)
        return None


def _get_task_timeout(identity: str) -> int:
    """Get task timeout for identity from config."""
    try:
        cfg = config.load_config()
        role_cfg = cfg.get("roles", {}).get(identity, {})
        return role_cfg.get("task_timeout", cfg.get("timeouts", {}).get("task_default", 120))
    except Exception as exc:
        log.warning(f"Failed to load config for {identity}, using default timeout: {exc}")
        return 120


def spawn_agents_from_mentions(channel_id: str, content: str) -> None:
    """Spawn agents from @mentions in message content."""
    try:
        from . import channels

        channel_name = channels.get_channel_name(channel_id)
        subprocess.run(
            [sys.argv[0], channel_id, channel_name, content],
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

    config.init_config()

    poll_cmd, poll_agents = _parse_poll_command(content)
    if poll_cmd == "poll" and poll_agents:
        log.info(f"Poll command detected for agents: {poll_agents}")
        from . import messaging

        for identity in poll_agents:
            try:
                agent_id = spawn.db.get_agent_id(identity)
                if not agent_id:
                    agent_id = spawn.db.ensure_agent(identity)
                from . import polls as polls_mod

                poll_id = polls_mod.create_poll(agent_id, channel_id, created_by="human")
                log.info(f"Created poll {poll_id} for {identity} in {channel_name}")
                messaging.send_message(channel_id, "system", f"🔴 Polling {identity}...")
            except Exception as e:
                log.error(f"Poll creation failed for {identity}: {e}")
        return

    dismiss_cmd, dismiss_agents = _parse_dismiss_command(content)
    if dismiss_cmd == "dismiss" and dismiss_agents:
        log.info(f"Dismiss command detected for agents: {dismiss_agents}")
        from . import messaging
        from . import polls as polls_mod

        for identity in dismiss_agents:
            try:
                agent_id = spawn.db.get_agent_id(identity)
                if agent_id:
                    dismissed = polls_mod.dismiss_poll(agent_id, channel_id)
                    if dismissed:
                        log.info(f"Dismissed poll for {identity} in {channel_name}")
                        messaging.send_message(channel_id, "system", f"⚪ Dismissed {identity}")
                    else:
                        log.info(f"No active poll for {identity}")
                else:
                    log.warning(f"Unknown agent: {identity}")
            except Exception as e:
                log.error(f"Poll dismissal failed for {identity}: {e}")
        return

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
                task_id = spawn.db.create_task(role=identity, input=prompt, channel_id=channel_id)
                spawn.db.update_task(task_id, status=TaskStatus.RUNNING, mark_started=True)

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
                    spawn.db.update_task(
                        task_id,
                        status=TaskStatus.COMPLETED,
                        output=result.stdout.strip(),
                        mark_completed=True,
                    )
                    results.append((identity, result.stdout.strip()))
                else:
                    spawn.db.update_task(
                        task_id, status=TaskStatus.FAILED, stderr=result.stderr, mark_completed=True
                    )
                    log.error(f"Spawn failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                spawn.db.update_task(
                    task_id,
                    status=TaskStatus.TIMEOUT,
                    stderr=f"Spawn timeout ({timeout}s)",
                    mark_completed=True,
                )
                log.error(f"Spawn timeout for {identity}")
            except Exception as e:
                spawn.db.update_task(
                    task_id, status=TaskStatus.FAILED, stderr=str(e), mark_completed=True
                )
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

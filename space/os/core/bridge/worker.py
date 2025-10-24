"""Worker for processing @mentions and spawning agents."""

import logging
import re
import subprocess
import sys

from space.os import config
from space.os.core.bridge import db
from space.os.core.spawn import db as spawn_db
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

    config.init_config()
    results = []
    for identity in mentions:
        log.info(f"Spawning {identity}")
        prompt = _build_prompt(identity, channel_name, content)
        if prompt:
            log.info(f"Got prompt, running spawn {identity}")
            timeout = _get_task_timeout(identity)
            try:
                task_id = spawn_db.create_task(
                    identity=identity, input=prompt, channel_id=channel_id
                )
                spawn_db.update_task(task_id, status=TaskStatus.RUNNING, mark_started=True)

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
                    spawn_db.update_task(
                        task_id,
                        status=TaskStatus.COMPLETED,
                        output=result.stdout.strip(),
                        mark_completed=True,
                    )
                    results.append((identity, result.stdout.strip()))
                else:
                    spawn_db.update_task(
                        task_id, status=TaskStatus.FAILED, stderr=result.stderr, mark_completed=True
                    )
                    log.error(f"Spawn failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                spawn_db.update_task(
                    task_id,
                    status=TaskStatus.TIMEOUT,
                    stderr=f"Spawn timeout ({timeout}s)",
                    mark_completed=True,
                )
                log.error(f"Spawn timeout for {identity}")
            except Exception as e:
                spawn_db.update_task(
                    task_id, status=TaskStatus.FAILED, stderr=str(e), mark_completed=True
                )
                log.error(f"Spawn error: {e}")
        else:
            log.warning(f"No prompt for {identity}")

    if results:
        for identity, output in results:
            db.send_message(channel_id, identity, output)
    elif mentions:
        log.warning(f"No results from spawning {len(mentions)} agent(s))")


if __name__ == "__main__":
    main()

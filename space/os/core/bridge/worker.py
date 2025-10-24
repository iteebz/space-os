"""Async worker for processing @mentions and spawning agents."""

import logging
import subprocess
import sys

from space.os import config
from space.os.core.bridge import parser
from space.os.core.bridge.api import messages as api_messages
from space.os.core.spawn import db as spawn_db

logging.basicConfig(level=logging.DEBUG, format="[worker] %(message)s")
log = logging.getLogger(__name__)


def _get_task_timeout(identity: str, default: int = 120) -> int:
    """Get task timeout for identity from config, fallback to default."""
    try:
        cfg = config.load_config()
        role_cfg = cfg.get("roles", {}).get(identity, {})
        return role_cfg.get("task_timeout", default)
    except Exception as exc:
        log.warning(f"Failed to load config for {identity}, using default timeout: {exc}")
        return default


def main():
    if len(sys.argv) != 4:
        log.error(f"Invalid args: {len(sys.argv)}, expected 4. argv={sys.argv}")
        return

    channel_id = sys.argv[1]
    channel_name = sys.argv[2]
    content = sys.argv[3]

    log.info(f"Processing channel={channel_name}, content={content[:50]}")
    mentions = parser.parse_mentions(content)
    log.info(f"Found mentions: {mentions}")
    if not mentions:
        log.info("No mentions, skipping")
        return

    config.init_config()
    results = []
    for identity in mentions:
        log.info(f"Spawning {identity}")
        prompt = parser.spawn_from_mention(identity, channel_name, content)
        if prompt:
            log.info(f"Got prompt, running spawn {identity}")
            timeout = _get_task_timeout(identity)
            try:
                task_id = spawn_db.create_task(
                    identity=identity, input=prompt, channel_id=channel_id
                )
                spawn_db.update_task(task_id, status="running", started_at=True)

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
                        task_id, status="completed", output=result.stdout.strip(), completed_at=True
                    )
                    results.append((identity, result.stdout.strip()))
                else:
                    spawn_db.update_task(
                        task_id, status="failed", stderr=result.stderr, completed_at=True
                    )
                    log.error(f"Spawn failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                spawn_db.update_task(
                    task_id,
                    status="timeout",
                    stderr=f"Spawn timeout ({timeout}s)",
                    completed_at=True,
                )
                log.error(f"Spawn timeout for {identity}")
            except Exception as e:
                spawn_db.update_task(task_id, status="failed", stderr=str(e), completed_at=True)
                log.error(f"Spawn error: {e}")
        else:
            log.warning(f"No prompt for {identity}")

    if results:
        for identity, output in results:
            api_messages.send_message(channel_id, identity, output)
    elif mentions:
        log.warning(f"No results from spawning {len(mentions)} agent(s)")


if __name__ == "__main__":
    main()

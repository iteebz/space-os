"""Async worker for processing @mentions and spawning agents."""

import logging
import subprocess
import sys
from datetime import datetime

from space.os.bridge import db, parser
from space.os.bridge.api import messages as api_messages
from space.os.lib.uuid7 import uuid7

logging.basicConfig(level=logging.DEBUG, format="[worker] %(message)s")
log = logging.getLogger(__name__)


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

    results = []
    for identity in mentions:
        log.info(f"Spawning {identity}")
        prompt = parser.spawn_from_mention(identity, channel_name, content)
        if prompt:
            log.info(f"Got prompt, running spawn {identity}")
            task_id = uuid7()
            try:
                _create_task(channel_id, task_id, identity, prompt, "pending")
                _update_task_status(task_id, "running", started_at=True)

                result = subprocess.run(
                    ["spawn", identity, prompt, "--channel", channel_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    stdin=subprocess.DEVNULL,
                )

                log.info(
                    f"Spawn returncode={result.returncode}, stdout_len={len(result.stdout)}, stderr={result.stderr[:100]}"
                )

                if result.returncode == 0 and result.stdout.strip():
                    _update_task_completion(task_id, "completed", result.stdout.strip(), None)
                    results.append((identity, result.stdout.strip()))
                else:
                    _update_task_completion(task_id, "failed", None, result.stderr)
                    log.error(f"Spawn failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                _update_task_completion(task_id, "timeout", None, "Spawn timeout")
                log.error(f"Spawn timeout for {identity}")
            except Exception as e:
                _update_task_completion(task_id, "failed", None, str(e))
                log.error(f"Spawn error: {e}")
        else:
            log.warning(f"No prompt for {identity}")

    if results:
        for identity, output in results:
            api_messages.send_message(channel_id, identity, output)
    elif mentions:
        log.warning(f"No results from spawning {len(mentions)} agent(s)")


def _create_task(channel_id: str, task_id: str, identity: str, input_text: str, status: str):
    """Create task record."""
    conn = db.get_db()
    now_iso = datetime.now().isoformat()
    conn.execute(
        """
        INSERT INTO tasks (uuid7, channel_id, identity, status, input, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (task_id, channel_id, identity, status, input_text, now_iso),
    )
    conn.commit()
    conn.close()


def _update_task_status(task_id: str, status: str, started_at: bool = False):
    """Update task status."""
    conn = db.get_db()
    if started_at:
        now_iso = datetime.now().isoformat()
        conn.execute(
            "UPDATE tasks SET status = ?, started_at = ? WHERE uuid7 = ?",
            (status, now_iso, task_id),
        )
    else:
        conn.execute("UPDATE tasks SET status = ? WHERE uuid7 = ?", (status, task_id))
    conn.commit()
    conn.close()


def _update_task_completion(task_id: str, status: str, output: str | None, stderr: str | None):
    """Update task on completion."""
    conn = db.get_db()
    now_iso = datetime.now().isoformat()
    conn.execute(
        """
        UPDATE tasks SET status = ?, output = ?, stderr = ?, completed_at = ?
        WHERE uuid7 = ?
        """,
        (status, output, stderr, now_iso, task_id),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()

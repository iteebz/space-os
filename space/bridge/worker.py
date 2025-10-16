"""Async worker for processing @mentions and spawning agents."""

import logging
import subprocess
import sys

from space.bridge import parser
from space.bridge.api import messages as api_messages

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
            try:
                result = subprocess.run(
                    ["spawn", identity, prompt, "--channel", channel_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    stdin=subprocess.DEVNULL,
                )
                log.info(
                    f"Spawn returncode={result.returncode}, stdout_len={len(result.stdout)}, stderr={result.stderr[:100]}"
                )
                if result.returncode == 0 and result.stdout.strip():
                    results.append((identity, result.stdout.strip()))
                elif result.returncode != 0:
                    log.error(f"Spawn failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                log.error(f"Spawn timeout for {identity}")
        else:
            log.warning(f"No prompt for {identity}")

    if results:
        for identity, output in results:
            api_messages.send_message(channel_id, identity, output)
    elif mentions:
        log.warning(f"No results from spawning {len(mentions)} agent(s)")


if __name__ == "__main__":
    main()

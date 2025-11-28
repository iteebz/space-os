"""Timer: poll channels and auto-stop agents when timer expires."""

import logging
import time
from datetime import datetime

from space.lib import store
from space.os.bridge.api import channels, messaging
from space.os.bridge.api.delimiters import _stop_all_agents_in_channel

log = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30


def run() -> None:
    """Poll channels with active timers and stop agents when expired."""
    log.info("Timer started")

    while True:
        try:
            _check_and_expire_timers()
        except Exception as e:
            log.error(f"Timer error: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL_SECONDS)


def _check_and_expire_timers() -> None:
    """Check all channels with timers and expire those past deadline."""
    with store.ensure() as conn:
        rows = conn.execute(
            """
            SELECT channel_id, name, timer_expires_at
            FROM channels
            WHERE timer_expires_at IS NOT NULL
            """
        ).fetchall()

    now = datetime.utcnow()

    for row in rows:
        channel_id = row["channel_id"]
        channel_name = row["name"]
        expires_at_str = row["timer_expires_at"]

        try:
            expires_at = datetime.fromisoformat(expires_at_str)
        except ValueError:
            log.warning(f"Invalid timer format for channel {channel_name}: {expires_at_str}")
            continue

        if now >= expires_at:
            log.info(f"Timer expired for channel {channel_name}, stopping all agents")
            _stop_all_agents_in_channel(channel_id)

            messaging.create_message(
                channel_id=channel_id,
                agent_id="system",
                content="⏱️ Timer expired. All agents stopped.",
            )

            channels.clear_timer(channel_id)

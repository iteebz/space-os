"""Bridge sidecar watcher."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path

from . import coordination
from .models import Message


def _default_log(message: str) -> None:
    print(message)


class AlertWriter:
    """Persist alerts to bridge.db."""

    def __init__(self, identity: str, base_dir: Path):
        from . import storage

        self.identity = identity
        self.storage = storage
        self.last_message_id = self._load_last_message_id()
        self.last_emit_ts: float = 0.0

    def _load_last_message_id(self) -> int:
        payload = self.storage.load_alert(self.identity)
        if not payload:
            return 0
        return int(payload.get("message_id", 0) or 0)

    def write(self, payload: dict) -> None:
        self.storage.save_alert(self.identity, payload)
        self.last_message_id = int(payload.get("message_id", self.last_message_id))
        self.last_emit_ts = time.time()

    def clear(self) -> None:
        pass


def pid_alive(pid: int) -> bool:
    """Check whether a process is still running."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    else:
        return True


CONSENSUS_TOKENS = {"!consensus", "!done", "!alert"}


def classify_message(message: Message, identity: str) -> tuple[list[str], bool]:
    """Return flags and mention detection for a message."""
    content_lower = message.content.lower()
    flags: list[str] = []
    if any(token in content_lower for token in CONSENSUS_TOKENS):
        flags.append("consensus")
    mentioned = f"@{identity}".lower() in content_lower
    if mentioned:
        flags.append("mention")
    return flags, mentioned


class SidecarRunner:
    """Main loop encapsulation."""

    def __init__(
        self,
        channel: str,
        identity: str,
        target_pid: int,
        poll_interval: float = 5.0,
        min_interval: float = 0.0,
        only_mentions: bool = False,
        include_consensus: bool = True,
        alerts_dir: Path | None = None,
        log: Callable[[str], None] = _default_log,
    ) -> None:
        self.channel = channel
        self.channel_id = coordination.resolve_channel_id(channel)
        self.identity = identity
        self.target_pid = target_pid
        self.poll_interval = poll_interval
        self.min_interval = min_interval
        self.only_mentions = only_mentions
        self.include_consensus = include_consensus
        self.writer = AlertWriter(identity, alerts_dir)
        self.log = log

    def run(self) -> None:
        self.log(f"Sidecar monitoring {self.identity} on {self.channel} (PID {self.target_pid})")
        try:
            while True:
                if not pid_alive(self.target_pid):
                    self.log("Target process terminated. Shutting down.")
                    self.writer.clear()
                    break

                self._poll_once()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            self.log("Sidecar interrupted. Cleaning up.")
            self.writer.clear()

    def _poll_once(self) -> None:
        try:
            messages, _ = coordination.recv_updates(self.channel_id, self.identity)[:2]
        except Exception as exc:
            self.log(f"Polling error: {exc}")
            return

        new_messages = [m for m in messages if m.id > self.writer.last_message_id]
        if not new_messages:
            return

        relevant = []
        consensus_messages = []
        for message in new_messages:
            flags, mentioned = classify_message(message, self.identity)
            is_consensus = "consensus" in flags
            if self.only_mentions and not mentioned:
                if self.include_consensus and is_consensus:
                    consensus_messages.append((message, flags))
                continue
            relevant.append((message, flags))

        if self.only_mentions and self.include_consensus:
            relevant.extend(consensus_messages)

        if not relevant:
            return

        if self.min_interval:
            elapsed = time.time() - self.writer.last_emit_ts
            if elapsed < self.min_interval:
                return

        message, flags = relevant[-1]

        instructions_data = coordination.channel_instructions(self.channel_id)
        instructions_content = instructions_data[1] if instructions_data else None

        payload = {
            "channel": message.channel_id,
            "message_id": message.id,
            "sender": message.sender,
            "timestamp": message.created_at,
            "body": message.content,
            "flags": flags,
            "unread_count": len(messages),
            "instructions": instructions_content,
        }
        self.writer.write(payload)


def run_sidecar(
    channel: str,
    identity: str,
    pid: int,
    *,
    poll_interval: float = 5.0,
    min_interval: float = 0.0,
    only_mentions: bool = False,
    include_consensus: bool = True,
    alerts_dir: Path | None = None,
    log: Callable[[str], None] = _default_log,
) -> None:
    """Entry point for CLI command."""
    runner = SidecarRunner(
        channel=channel,
        identity=identity,
        target_pid=pid,
        poll_interval=poll_interval,
        min_interval=min_interval,
        only_mentions=only_mentions,
        include_consensus=include_consensus,
        alerts_dir=alerts_dir,
        log=log,
    )
    runner.run()


def load_alert_payload(identity: str, alerts_dir: Path | None = None) -> dict | None:
    """Load alert payload for identity if present."""
    from . import storage

    return storage.load_alert(identity)


__all__ = [
    "run_sidecar",
    "load_alert_payload",
]

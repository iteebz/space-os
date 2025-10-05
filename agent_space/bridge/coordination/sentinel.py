"""Sentinel audit logging for security escalations."""

from __future__ import annotations

import datetime as _dt

from .. import config

SENTINEL_CHANNEL = "cogency-sec"


def log_security_event(channel: str, sender: str, content: str, *, force: bool = False) -> None:
    """Append security event to the sentinel audit log."""
    if not force and channel != SENTINEL_CHANNEL:
        return

    severity, message = _parse_message(content)
    timestamp = _dt.datetime.now(tz=_dt.timezone.utc).isoformat()
    sanitised = " ".join(message.splitlines()).strip() or "(empty message)"

    line = f"{timestamp} [{severity}] {sender}@{channel} {sanitised}\n"

    log_path = config.resolve_sentinel_log_path()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _parse_message(content: str) -> tuple[str, str]:
    text = content.strip()
    if text.startswith("[") and "]" in text:
        label, remainder = text[1:].split("]", 1)
        severity = label.strip().upper() or "INFO"
        message = remainder.strip()
    else:
        severity = "INFO"
        message = text
    return severity, message

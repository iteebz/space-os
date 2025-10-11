"""Identity helpers."""

from __future__ import annotations

import secrets
import threading
import time
import uuid

_RAND_BITS = 80
_RAND_MASK = (1 << _RAND_BITS) - 1
_state_lock = threading.Lock()
_last_ts_ms = 0
_last_rand = secrets.randbits(_RAND_BITS)


def _next_timestamp_ms() -> int:
    return int(time.time_ns() // 1_000_000)


def _next_random(ts_ms: int) -> tuple[int, int]:
    global _last_ts_ms, _last_rand

    with _state_lock:
        current_ts = _next_timestamp_ms()
        if current_ts > ts_ms:
            ts_ms = current_ts

        if ts_ms > _last_ts_ms:
            _last_ts_ms = ts_ms
            _last_rand = secrets.randbits(_RAND_BITS)
        else:
            _last_rand = (_last_rand + 1) & _RAND_MASK
            if _last_rand == 0:
                _last_ts_ms += 1
                ts_ms = _last_ts_ms
                _last_rand = secrets.randbits(_RAND_BITS)
            ts_ms = _last_ts_ms

        return ts_ms, _last_rand


def uuid7() -> str:
    """Return monotonically increasing UUID7 hex string."""
    ts_ms = _next_timestamp_ms()
    ts_ms, random_bits = _next_random(ts_ms)

    ts_bytes = ts_ms.to_bytes(6, byteorder="big")
    rand_bytes = random_bits.to_bytes(10, byteorder="big")

    raw = bytearray(ts_bytes + rand_bytes)
    raw[6] &= 0x0F
    raw[6] |= 0x70  # version 7
    raw[8] &= 0x3F
    raw[8] |= 0x80  # IETF variant

    return uuid.UUID(bytes=bytes(raw)).hex


def short_id(full_uuid: str) -> str:
    """Return last 8 chars of UUID for display/matching.

    UUID7 structure: [48-bit timestamp][74-bit random]
    First chars = timestamp-dominated (low entropy, visual clustering)
    Last chars = high entropy suffix (good collision resistance)

    Like git short refs: keep full UUID in DB, display short for humans.
    """
    return full_uuid[-8:]


__all__ = ["uuid7", "short_id"]

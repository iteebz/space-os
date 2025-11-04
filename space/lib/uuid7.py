from __future__ import annotations

import secrets
import threading
import time
import uuid as _uuid

from space.lib import store

# Monotonic state for same-millisecond IDs (RFC 9562 Method 2)
_state_lock = threading.Lock()
_last_timestamp_ms = 0
_counter = 0

# Check for native uuid7 support once at module load
_USE_NATIVE = hasattr(_uuid, "uuid7")


def uuid7() -> str:
    """Generate UUID v7 (time-ordered) for distributed-safe IDs."""
    if _USE_NATIVE:
        return str(_uuid.uuid7())

    global _last_timestamp_ms, _counter

    with _state_lock:
        timestamp_ms = int(time.time() * 1000)

        # RFC 9562 Method 2: Monotonic counter for same-millisecond IDs
        if timestamp_ms == _last_timestamp_ms:
            _counter = (_counter + 1) & 0xFFF  # 12-bit counter wraps
        else:
            _counter = secrets.randbits(12)
            _last_timestamp_ms = timestamp_ms

        # RFC 9562: 48-bit timestamp + 4-bit version + 12-bit counter
        time_high = (timestamp_ms >> 16) & 0xFFFFFFFF
        time_low = timestamp_ms & 0xFFFF

        # Version field: 0111 (7) in bits 12-15
        time_low_and_version = (time_low << 16) | (7 << 12) | _counter

        # Variant field: 10 in bits 0-1, followed by 62 bits random
        rand_b_high = secrets.randbits(14)
        rand_b_low = secrets.randbits(48)
        variant_and_rand = (0b10 << 62) | (rand_b_high << 48) | rand_b_low

        # Assemble 128-bit UUID
        uuid_int = (time_high << 96) | (time_low_and_version << 64) | variant_and_rand

        return str(_uuid.UUID(int=uuid_int))


def short_id(full_uuid: str) -> str:
    """Return last 8 chars: 32 bits of collision-resistant randomness.

    Last 8 = variant + random. Works for UUID4 (all random) and UUID7
    (timestamp + random tail). UUID7 prefix is timestamp-only (collides
    on rapid generation). Suffix is always high-entropy.
    """
    return full_uuid[-8:]


def resolve_id(table: str, id_col: str, partial_id: str, *, error_context: str = "") -> str:
    """Resolve partial/suffix ID to full ID via fuzzy suffix matching.

    Args:
        table: Table name to query
        id_col: Column name containing the IDs
        partial_id: Partial ID (suffix match)
        error_context: Additional context for error messages

    Returns:
        Full ID if unambiguous match found

    Raises:
        ValueError: If no match, ambiguous matches, or invalid identifiers
    """
    _validate_identifier(table, "table")
    _validate_identifier(id_col, "column")

    if not partial_id or not isinstance(partial_id, str):
        raise ValueError("partial_id must be a non-empty string")

    with store.ensure() as conn:
        rows = conn.execute(
            f"SELECT {id_col} FROM {table} WHERE {id_col} LIKE ?",
            (f"%{partial_id}",),
        ).fetchall()

    if not rows:
        msg = f"No entry found with ID ending in '{partial_id}'"
        if error_context:
            msg += f" ({error_context})"
        raise ValueError(msg)

    if len(rows) > 1:
        ambiguous_ids = [row[0] for row in rows]
        msg = f"Ambiguous ID: '{partial_id}' matches multiple entries: {ambiguous_ids}"
        if error_context:
            msg += f" ({error_context})"
        raise ValueError(msg)

    return rows[0][0]


def _validate_identifier(name: str, kind: str) -> None:
    """Validate table/column names against basic injection patterns.

    Not a whitelist (vestigial). Just reject obvious SQL injection attempts.
    Callers are internal and know what tables they're querying.
    """
    if not name or not isinstance(name, str):
        raise ValueError(f"Invalid {kind}: must be non-empty string")

    name = name.strip()
    if not name:
        raise ValueError(f"Invalid {kind}: cannot be whitespace-only")

    if not name.isidentifier():
        raise ValueError(f"Invalid {kind}: '{name}' contains illegal characters")

    if name != name.lower():
        raise ValueError(f"Invalid {kind}: '{name}' must be lowercase")


__all__ = ["uuid7", "short_id", "resolve_id"]

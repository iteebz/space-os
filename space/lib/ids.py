"""ID utilities: generation, resolution, formatting."""

from __future__ import annotations

from space.lib import store

_VALID_TABLES = {"agents", "channels", "memories", "knowledge", "messages", "events", "memory"}
_VALID_COLUMNS = {
    "agent_id",
    "channel_id",
    "message_id",
    "memory_id",
    "knowledge_id",
    "event_id",
    "note_id",
    "task_id",
}


def resolve_id(table: str, id_col: str, partial_id: str, *, error_context: str = "") -> str:
    """Resolve a partial/suffix ID to full ID via fuzzy matching.

    Args:
        table: Table name to query (validated against whitelist)
        id_col: Column name containing the IDs (validated against whitelist)
        partial_id: Partial ID (suffix match)
        error_context: Additional context for error messages

    Returns:
        Full ID if unambiguous match found

    Raises:
        ValueError: If no match, ambiguous matches, or invalid identifiers
    """
    if table not in _VALID_TABLES:
        raise ValueError(f"Invalid table: {table}")
    if id_col not in _VALID_COLUMNS:
        raise ValueError(f"Invalid column: {id_col}")

    table_map = {"memory": "memories"}
    actual_table = table_map.get(table, table)
    with store.ensure() as conn:
        rows = conn.execute(
            f"SELECT {id_col} FROM {actual_table} WHERE {id_col} LIKE ?",
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


def truncate_uuid(uuid: str, length: int = 8) -> str:
    """Return first N characters of UUID (default 8 hex digits).

    Args:
        uuid: Full UUID string (must be non-empty and contain only valid UUID chars)
        length: Number of characters to return (default 8, must be 1-36)

    Returns:
        Truncated UUID string

    Raises:
        ValueError: If uuid is empty or contains invalid characters
        ValueError: If length is not in range 1-36
    """
    if not uuid:
        raise ValueError("UUID cannot be empty")

    if not (1 <= length <= 36):
        raise ValueError(f"Length must be 1-36, got {length}")

    if not all(c in "0123456789abcdefABCDEF-" for c in uuid):
        raise ValueError(f"Invalid UUID characters in '{uuid}'")

    return uuid[:length]

from __future__ import annotations

from space.os import db


def resolve_id(table: str, id_col: str, partial_id: str, *, error_context: str = "") -> str:
    """Resolve a partial/suffix ID to full ID via fuzzy matching.

    Args:
        table: Table name to query
        id_col: Column name containing the IDs
        partial_id: Partial ID (suffix match)
        error_context: Additional context for error messages

    Returns:
        Full ID if unambiguous match found

    Raises:
        ValueError: If no match or ambiguous matches
    """
    with db.ensure(table.replace(".db", "")) as conn:
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

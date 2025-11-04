"""SQL query builders and helpers."""


def archive_filter(show_all: bool, prefix: str = "WHERE") -> str:
    """Build archive clause for queries.

    Args:
        show_all: If True, return empty string (no filtering)
        prefix: Prefix to use ("WHERE", "AND", or "")

    Returns:
        Formatted clause like "WHERE archived_at IS NULL" or "AND archived_at IS NULL" or ""
    """
    if show_all:
        return ""
    return f"{prefix} archived_at IS NULL"


__all__ = ["archive_filter"]

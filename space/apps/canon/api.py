"""Canon API - structured access to ~/space/canon documents."""

from __future__ import annotations

from pathlib import Path

from space.lib import errors
from space.lib.paths import canon_path


def search(query: str, max_content_length: int = 500) -> list[dict]:
    """Search canon documents for query matches."""
    if not query:
        return []

    canon_root = canon_path()
    if not canon_root.exists():
        return []

    matches: list[dict] = []
    for md_file in canon_root.rglob("*.md"):
        _append_match_if_relevant(matches, md_file, canon_root, query, max_content_length)
    return matches


def _append_match_if_relevant(
    matches: list[dict],
    md_file: Path,
    canon_root: Path,
    query: str,
    max_content_length: int,
) -> None:
    """Append match dict to results if query exists in markdown file."""
    try:
        content = md_file.read_text()
    except Exception as exc:  # pragma: no cover - logged for diagnostics
        errors.log_error("canon", None, exc, "file read")
        return

    if query.lower() not in content.lower():
        return

    relative_path = md_file.relative_to(canon_root)
    truncated_content = content[:max_content_length] + (
        "..." if len(content) > max_content_length else ""
    )
    matches.append(
        {
            "source": "canon",
            "path": str(relative_path),
            "content": truncated_content,
            "reference": f"canon:{relative_path}",
        }
    )

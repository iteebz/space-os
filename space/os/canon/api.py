"""Canon operations: read-only git-backed markdown files."""

import contextlib

from space.core.models import Canon
from space.lib.paths import canon_path


def get_canon_entries() -> dict:
    """Get all canon markdown files organized hierarchically."""
    canon_root = canon_path()
    if not canon_root.exists():
        return {}

    tree = {}
    for md_file in canon_root.rglob("*.md"):
        rel_path = md_file.relative_to(canon_root)
        path_str = str(rel_path).replace("\\", "/")
        path_str = path_str[:-3] if path_str.endswith(".md") else path_str

        parts = path_str.split("/")
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]

    return tree


def read_canon(path: str) -> Canon | None:
    """Read a canon markdown file.

    Args:
        path: Path like "architecture/caching.md" or "architecture/caching"

    Returns:
        Canon object or None if not found
    """
    canon_root = canon_path()

    if not path.endswith(".md"):
        path = f"{path}.md"

    file_path = canon_root / path

    if not file_path.exists():
        return None

    if not file_path.is_file():
        return None

    try:
        rel_path = file_path.relative_to(canon_root)
        path_str = str(rel_path).replace("\\", "/")
        if path_str.endswith(".md"):
            path_str = path_str[:-3]

        with open(file_path) as f:
            content = f.read()

        return Canon(
            path=path_str,
            content=content,
            created_at=None,
        )
    except (OSError, ValueError):
        return None


def canon_exists(path: str) -> bool:
    """Check if a canon file exists."""
    canon_root = canon_path()

    if not path.endswith(".md"):
        path = f"{path}.md"

    file_path = canon_root / path
    return file_path.is_file()


def search(
    query: str, identity: str | None = None, all_agents: bool = False, max_content_length: int = 500
) -> list[dict]:
    """Search canon documents by query."""
    if not query:
        return []

    canon_root = canon_path()
    if not canon_root.exists():
        return []

    matches: list[dict] = []
    for md_file in canon_root.rglob("*.md"):
        try:
            content = md_file.read_text()
        except Exception:
            continue

        if query.lower() not in content.lower():
            continue

        relative_path = md_file.relative_to(canon_root)
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "..."

        matches.append(
            {
                "source": "canon",
                "path": str(relative_path),
                "content": truncated_content,
                "reference": f"canon:{relative_path}",
            }
        )

    return matches


def stats() -> dict:
    """Get canon statistics."""
    canon_root = canon_path()
    if not canon_root.exists():
        return {
            "available": False,
            "total_files": 0,
            "total_size_bytes": 0,
        }

    total_files = 0
    total_size = 0
    for md_file in canon_root.rglob("*.md"):
        total_files += 1
        with contextlib.suppress(OSError):
            total_size += md_file.stat().st_size

    return {
        "available": True,
        "total_files": total_files,
        "total_size_bytes": total_size,
    }

import contextlib

from space.core.models import Canon
from space.lib.paths import canon_path


def _normalize_path(path_str: str) -> str:
    """Normalize file path: cross-platform + remove .md extension."""
    path_str = path_str.replace("\\", "/")
    if path_str.endswith(".md"):
        path_str = path_str[:-3]
    return path_str


def get_canon_entries() -> dict:
    """Get all canon markdown files organized hierarchically."""
    canon_root = canon_path()
    if not canon_root.exists():
        return {}

    tree = {}
    for md_file in canon_root.rglob("*.md"):
        rel_path = md_file.relative_to(canon_root)
        path_str = _normalize_path(str(rel_path))

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
        path_str = _normalize_path(str(rel_path))

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
    """Search canon documents by filename and content, prioritizing filename matches."""
    if not query:
        return []

    canon_root = canon_path()
    if not canon_root.exists():
        return []

    query_lower = query.lower()
    path_matches = []
    content_matches = []

    for md_file in sorted(canon_root.rglob("*.md")):
        relative_path = md_file.relative_to(canon_root)
        path_str = str(relative_path).lower()
        path_match = query_lower in path_str

        if not path_match:
            try:
                content = md_file.read_text()
                content_match = query_lower in content.lower()
                if not content_match:
                    continue
            except Exception:
                continue
        else:
            try:
                content = md_file.read_text()
            except Exception:
                continue

        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "…"

        result = {
            "source": "canon",
            "path": str(relative_path),
            "content": truncated_content,
            "reference": f"canon:{relative_path}",
        }

        if path_match:
            path_matches.append(result)
        else:
            content_matches.append(result)

    return path_matches + content_matches


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

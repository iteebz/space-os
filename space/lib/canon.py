"""Canon document search."""

from space.lib import errors
from space.lib.paths import canon_path


def search(query: str, max_content_length: int = 500) -> list[dict]:
    """Search canon documents for relevant sections."""
    matches = []
    try:
        canon_root = canon_path()
        if not canon_root.exists():
            return []

        if not query:
            return []

        for md_file in canon_root.rglob("*.md"):
            try:
                content = md_file.read_text()
                if query.lower() in content.lower():
                    matches.append(
                        {
                            "source": "canon",
                            "path": str(md_file.relative_to(canon_root)),
                            "content": content[:max_content_length]
                            + ("..." if len(content) > max_content_length else ""),
                            "reference": f"canon:{md_file.relative_to(canon_root)}",
                        }
                    )
            except Exception as e:
                errors.log_error("canon", None, e, "file processing")
    except Exception as e:
        errors.log_error("canon", None, e, "directory traversal")
    return matches

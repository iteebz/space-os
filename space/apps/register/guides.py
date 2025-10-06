from pathlib import Path
import hashlib

from space.os.lib.fs import root
from . import api as registry_api


def _prompts_guides_dir() -> Path:
    """Return the absolute path to the prompts/guides directory."""
    return root() / "prompts" / "guides"


def get_guide_from_registry(guide_hash: str) -> str | None:
    """Retrieve guide content from the registry by its hash."""
    return registry_api.get_constitution_content(guide_hash)


def load_guide_content(guide_name: str, guide_path: Path | None = None, guide_hash: str | None = None) -> str:
    """
    Load the content of a guide.
    Prioritizes loading from registry if guide_hash is provided.
    If guide_path is provided, loads from there and auto-registers if not already tracked.
    Falls back to default prompts/guides directory if neither is provided.
    """
    # 1. Try to load from registry by hash if provided
    if guide_hash:
        content = get_guide_from_registry(guide_hash)
        if content:
            return content

    # 2. If guide_path is provided, load from there and auto-register
    if guide_path:
        if not guide_path.exists():
            raise FileNotFoundError(f"Guide file not found: {guide_path}")
        content = guide_path.read_text()
        current_hash = hash_content(content)
        # Check if already tracked, if not, track it
        if not get_guide_from_registry(current_hash):
            track_guide_in_registry(current_hash, content)
        return content

    # 3. Fallback to default prompts/guides directory
    default_guide_path = _prompts_guides_dir() / f"{guide_name}.md"
    if not default_guide_path.exists():
        raise FileNotFoundError(f"Guide file not found: {default_guide_path}")
    content = default_guide_path.read_text()
    current_hash = hash_content(content)
    # Auto-register default guide if not already tracked
    if not get_guide_from_registry(current_hash):
        track_guide_in_registry(current_hash, content)
    return content


def hash_content(content: str) -> str:
    """Generate an 8-character hash for the given content."""
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def track_guide_in_registry(guide_hash: str, guide_content: str):
    """Track a guide in the registry, similar to constitutions."""
    registry_api.track_constitution(guide_hash, guide_content)

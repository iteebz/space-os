from pathlib import Path
import hashlib

from space.lib.fs import root
from . import api as registry_api


def _prompts_guides_dir() -> Path:
    """Return the absolute path to the prompts/guides directory."""
    return root() / "prompts" / "guides"


def get_guide_from_registry(guide_hash: str) -> str | None:
    """Retrieve guide content from the registry by its hash."""
    return registry_api.get_constitution_content(guide_hash)


def load_guide_content(guide_name: str, guide_hash: str | None = None) -> str:
    """
    Load the content of a guide.
    First tries to load from registry if guide_hash is provided, then falls back to file system.
    """
    if guide_hash:
        content = get_guide_from_registry(guide_hash)
        if content:
            return content

    guide_path = _prompts_guides_dir() / f"{guide_name}.md"
    if not guide_path.exists():
        raise FileNotFoundError(f"Guide file not found: {guide_path}")
    return guide_path.read_text()


def hash_content(content: str) -> str:
    """Generate an 8-character hash for the given content."""
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def track_guide_in_registry(guide_hash: str, guide_content: str):
    """Track a guide in the registry, similar to constitutions."""
    registry_api.track_constitution(guide_hash, guide_content)

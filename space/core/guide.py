from pathlib import Path
from typing import Optional

from space.apps import registry
from space.lib import fs, sha256


def get_guide_path(guide_name: str) -> Path:
    """Returns the absolute path to a guide file."""
    return fs.root() / "space" / "prompts" / "guides" / f"{guide_name}.md"


def load_guide_content(guide_name: str) -> Optional[str]:
    """Loads the content of a guide file."""
    guide_path = get_guide_path(guide_name)
    if guide_path.exists():
        return guide_path.read_text()
    return None


def hash_guide_content(content: str) -> str:
    """Hashes the content of a guide."""
    return sha256.sha256(content)


def track_guide_in_registry(guide_name: str, content: str):
    """Tracks a guide in the registry app."""
    guide_hash = hash_guide_content(content)
    registry.track_constitution(guide_hash, content)

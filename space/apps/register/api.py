from pathlib import Path
from typing import Optional

from space.os.lib import fs, sha256
from . import db
from .models import Entry


def get_guide_path(guide_name: str) -> Path:
    """Returns the absolute path to a guide file, checking app-specific and registry paths."""
    # Check for guides within the registry app itself (e.g., onboarding.md)
    registry_guide_path = fs.root() / "space" / "apps" / "registry" / "prompts" / "guides" / f"{guide_name}.md"
    if registry_guide_path.exists():
        return registry_guide_path

    # Check for app-specific guides (e.g., memory.md for the 'memory' app)
    # This assumes guide_name can also be an app_name for app-specific guides.
    app_guide_path = fs.root() / "space" / "apps" / guide_name / "prompts" / "guides" / f"{guide_name}.md"
    if app_guide_path.exists():
        return app_guide_path

    # Fallback to the old global prompts/guides directory (to be deprecated)
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


def fetch_by_sender(sender_id: str) -> Entry | None:
    """Fetch a registry entry by sender_id."""
    return db.fetch_by_sender(sender_id)


def track_constitution(constitution_hash: str, constitution_content: str):
    """Track a constitution in the database."""
    db.track_constitution(constitution_hash, constitution_content)


def get_constitution_content(constitution_hash: str) -> str | None:
    """Retrieve constitution content from the database by its hash."""
    return db.get_constitution_content(constitution_hash)


def link(
    agent_id: str,
    role: str,
    channels: list[str],
    constitution_hash: str,
    constitution_content: str,
    provider: str | None,
    model: str | None,
):
    """Link an agent to the registry."""
    db.link(
        agent_id=agent_id,
        role=role,
        channels=channels,
        constitution_hash=constitution_hash,
        constitution_content=constitution_content,
        provider=provider,
        model=model,
    )


def list_constitutions() -> list[tuple[str, str]]:
    """List all constitutions."""
    return db.list_constitutions()
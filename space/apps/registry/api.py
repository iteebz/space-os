

from . import db
from .models import Entry


def fetch_by_sender(sender_id: str) -> Entry | None:
    """Fetch a registry entry by sender_id."""
    return db.fetch_by_sender(sender_id)


def track_constitution(constitution_hash: str, constitution_content: str):
    """Track a constitution in the database."""
    db.track_constitution(constitution_hash, constitution_content)


def get_constitution_content(constitution_hash: str) -> str | None:
    """Retrieve constitution content by its hash."""
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

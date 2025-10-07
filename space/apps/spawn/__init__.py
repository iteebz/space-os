from space.apps.spawn.repo import SpawnRepo
from space.apps.spawn.models import Identity, Constitution
from space.os.events import track
from space.os.lib import uuid7

__all__ = ["add_identity", "get_identity", "add_constitution", "update_identity_current_constitution"]

def _get_repo():
    """Initializes and returns a SpawnRepo instance."""
    repo = SpawnRepo()
    repo.initialize()
    return repo

def add_identity(id: str, type: str, initial_constitution_content: str | None = None) -> Identity:
    repo = _get_repo()
    identity = repo.add_identity(id, type)
    track(
        source="spawn",
        event_type="identity.created",
        identity=identity.id,
        data={
            "identity_id": identity.id,
            "identity_type": identity.type,
            "initial_constitution_content": initial_constitution_content
        }
    )
    if initial_constitution_content:
        constitution_id = str(uuid7.uuid7())
        track(
            source="spawn",
            event_type="constitution_created",
            identity=identity.id,
            data={
                "constitution_id": constitution_id,
                "content": initial_constitution_content
            }
        )
    return identity

def get_identity(id: str) -> Identity | None:
    repo = _get_repo()
    return repo.get_identity(id)

def add_constitution(name: str, version: str, content: str, identity_id: str, created_by: str, change_description: str, previous_version_id: str | None = None) -> Constitution:
    repo = _get_repo()
    return repo.add_constitution(name, version, content, identity_id, created_by, change_description, previous_version_id)

def update_identity_current_constitution(identity_id: str, constitution_id: str):
    repo = _get_repo()
    repo.update_identity_current_constitution(identity_id, constitution_id)

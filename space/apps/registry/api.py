from typing import Optional, List
from .models import Identity, Constitution

# Module-level variable to hold the app instance
registry_app_instance = None

def _set_registry_app_instance(app_instance):
    """
    Setter for the module-level app instance.
    Called by the app's __init__.py to inject the app instance.
    """
    global registry_app_instance
    registry_app_instance = app_instance

def add_identity(id: str, type: str, initial_constitution_hash: Optional[str] = None) -> Identity:
    """Adds a new identity to the registry."""
    if not registry_app_instance:
        raise RuntimeError("Registry app instance not set.")
    repo = registry_app_instance.repositories["registry"]
    return repo.add_identity(id, type, initial_constitution_content)

def get_identity(id: str) -> Optional[Identity]:
    """Retrieves an identity by ID."""
    if not registry_app_instance:
        raise RuntimeError("Registry app instance not set.")
    repo = registry_app_instance.repositories["registry"]
    return repo.get_identity(id)

def add_constitution_version(
    name: str,
    content: str,
    identity_id: Optional[str] = None,
    change_description: Optional[str] = None,
    created_by: str = "system",
) -> Constitution:
    """Adds a new version of a constitution or guide."""
    from space.os.lib import sha256

    if not registry_app_instance:
        raise RuntimeError("Registry app instance not set.")
    repo = registry_app_instance.repositories["registry"]
    constitution_hash = sha256.sha256(content)
    return repo.add_constitution_version(name, content, constitution_hash, change_description, created_by)

def get_current_constitution_for_identity(identity_id: str) -> Optional[Constitution]:
    """Retrieves the current constitution for a given identity."""
    if not registry_app_instance:
        raise RuntimeError("Registry app instance not set.")
    repo = registry_app_instance.repositories["registry"]
    return repo.get_current_constitution_for_identity(identity_id)

def get_constitution_version(id: str) -> Optional[Constitution]:
    """Retrieves a specific constitution version by its ID."""
    if not registry_app_instance:
        raise RuntimeError("Registry app instance not set.")
    repo = registry_app_instance.repositories["registry"]
    return repo.get_constitution_version(id)

def get_constitution_history_for_identity(identity_id: str) -> List[Constitution]:
    """Retrieves all historical versions of constitutions for an identity."""
    if not registry_app_instance:
        raise RuntimeError("Registry app instance not set.")
    repo = registry_app_instance.repositories["registry"]
    return repo.get_constitution_history_for_identity(identity_id)

def get_constitution_history_by_name(name: str) -> List[Constitution]:
    """Retrieves all historical versions of a constitution/guide by name."""
    if not registry_app_instance:
        raise RuntimeError("Registry app instance not set.")
    repo = registry_app_instance.repositories["registry"]
    return repo.get_constitution_history_by_name(name)

def get_constitution_by_hash(constitution_hash: str) -> Optional[Constitution]:
    """Retrieves a constitution by its SHA256 hash."""
    if not registry_app_instance:
        raise RuntimeError("Registry app instance not set.")
    repo = registry_app_instance.repositories["registry"]
    return repo.get_constitution_by_hash(constitution_hash)

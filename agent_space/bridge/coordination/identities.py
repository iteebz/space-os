from spawn import registry

from .. import config, utils


def load_identity(sender_id: str, topic: str) -> tuple[str, str]:
    """Load identity from registry with hash verification."""
    reg = registry.get_registration_by_sender(sender_id, topic)
    if not reg:
        raise ValueError(f"Unregistered sender: {sender_id}")

    file_path = config._get_identity_file(sender_id)
    if not file_path.exists():
        raise FileNotFoundError(f"Identity file missing: {sender_id}")

    content = file_path.read_text()
    digest = utils.hash_digest(content)

    if digest != reg.constitution_hash:
        raise ValueError(f"Constitution hash mismatch for {sender_id}")

    return content, digest


def verify_sender(sender_id: str, topic: str) -> bool:
    """Verify sender has valid registration with matching hash."""
    try:
        load_identity(sender_id, topic)
        return True
    except (ValueError, FileNotFoundError):
        return False

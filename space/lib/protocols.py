from pathlib import Path
import hashlib

from ..spawn import registry

PROTOCOL_DIR = Path(__file__).parent.parent.parent / "protocols"

def load(protocol_name: str) -> str:
    """Loads a protocol file by name and returns its content."""
    protocol_path = PROTOCOL_DIR / f"{protocol_name}.md"
    if not protocol_path.exists():
        raise FileNotFoundError(f"Protocol file not found: {protocol_path}")
    content = protocol_path.read_text()
    
    protocol_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    registry.save_constitution(protocol_hash, content)
    
    return content

def hash_protocol(protocol_name: str) -> str:
    """Loads a protocol file by name, hashes its content, and returns the hash."""
    content = load(protocol_name) # load already saves the hash
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def get_content_by_hash(protocol_hash: str) -> str | None:
    """Retrieves protocol content from spawn.db by its hash."""
    return registry.get_constitution(protocol_hash)

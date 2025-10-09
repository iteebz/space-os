import hashlib
from pathlib import Path

README = Path(__file__).parent.parent.parent / "README.md"


def load(section_heading: str) -> str:
    """Extract section from README.md by heading.

    Args:
        section_heading: Markdown heading (e.g., "## Bridge", "### spawn")

    Returns:
        Section content from heading to next same-level heading
    """
    if not README.exists():
        raise FileNotFoundError(f"README not found: {README}")

    content = README.read_text()
    lines = content.split("\n")

    # Determine heading level
    level = len(section_heading.split()[0])  # Count '#' chars

    section = []
    capturing = False

    for line in lines:
        # Check if this is our target heading
        if line.strip() == section_heading.strip():
            capturing = True
            section.append(line)
            continue

        # If capturing and hit same-level heading, stop
        if capturing and line.startswith("#" * level + " "):
            break

        if capturing:
            section.append(line)

    if not section:
        raise ValueError(f"Section '{section_heading}' not found in README")

    return "\n".join(section).strip()


def hash_protocol(protocol_name: str) -> str:
    """Loads a protocol file by name, hashes its content, and returns the hash."""
    content = load(protocol_name)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def save_protocol(protocol_name: str) -> str:
    """Load protocol, save to spawn registry, return hash."""
    from ..spawn import registry

    registry.init_db()
    content = load(protocol_name)
    protocol_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    registry.save_constitution(protocol_hash, content)
    return protocol_hash


def get_content_by_hash(protocol_hash: str) -> str | None:
    """Retrieves protocol content from spawn.db by its hash."""
    from ..spawn import registry

    return registry.get_constitution(protocol_hash)

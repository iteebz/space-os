"""README lattice extraction pattern.

Single source of truth: main README.md contains all protocol documentation.
CLIs extract their sections via lattice.load(heading).

Pattern:
- space/handover/README.md or space/{module}/README.md = detailed protocol
- Main README.md = single source of truth for CLI help text
- lattice.load("### handover") extracts section when CLI runs
- Update README.md = all CLIs update automatically

Zero duplication. Impossible drift. Documentation IS executable.
"""

import hashlib
from pathlib import Path


def _resolve_readme() -> Path:
    """Locate README in both source tree and installed package layouts."""
    base = Path(__file__).resolve()
    candidates = [
        base.parents[2] / "README.md",
        base.parents[1] / "README.md",
        Path.cwd() / "README.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"README not found in any known location: {candidates}")


README = _resolve_readme()


def load(section_heading: str) -> str:
    """Extract section from README.md by heading.

    Args:
        section_heading: Markdown heading (e.g., "## Orientation", "# handover")

    Returns:
        Section content (heading stripped if h1)
    """
    if not README.exists():
        raise FileNotFoundError(f"README not found: {README}")

    content = README.read_text()
    lines = content.split("\n")

    level = section_heading.count("#")

    section = []
    capturing = False

    for line in lines:
        if line.strip() == section_heading.strip():
            capturing = True
            if level > 1:
                section.append(line)
            continue

        if capturing and line.startswith("#"):
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

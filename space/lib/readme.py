"""README lattice extraction pattern.

SSOT: Module READMEs are the source of truth.
CLIs load their module README directly via load_module(name).

Pattern:
- space/{module}/README.md = protocol personality + instructions
- CLI → load_module("bridge") → space/bridge/README.md
- Update module README = CLI updates automatically

Zero duplication. Impossible drift. Documentation IS executable.
"""

import hashlib
from pathlib import Path

README = Path(__file__).resolve().parents[2] / "README.md"


def _resolve_module_readme(module_name: str) -> Path:
    """Locate module README in source tree."""
    base = Path(__file__).resolve()
    candidates = [
        base.parents[1] / module_name / "README.md",
        base.parents[0] / module_name / "README.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"README not found for module {module_name}: {candidates}")


def load(module_name: str) -> str:
    """Load full README for a module."""
    readme_path = _resolve_module_readme(module_name)
    return readme_path.read_text().strip()


def load_section(section_heading: str) -> str:
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
    content = load_section(protocol_name)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def save_protocol(protocol_name: str) -> str:
    """Load protocol, save to spawn registry, return hash."""
    from ..spawn import registry

    registry.init_db()
    content = load_section(protocol_name)
    protocol_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    registry.save_constitution(protocol_hash, content)
    return protocol_hash


def get_content_by_hash(protocol_hash: str) -> str | None:
    """Retrieves protocol content from spawn.db by its hash."""
    from ..spawn import registry

    return registry.get_constitution(protocol_hash)

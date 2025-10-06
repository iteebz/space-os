from __future__ import annotations

from pathlib import Path


def root() -> Path:
    """Return the workspace root that owns the spawn project."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent

    return Path.cwd()


SPACE_DIR = root() / ".space"

def get_database_path(name: str) -> Path:
    """Return absolute path to a database file under the workspace .space directory."""
    path = SPACE_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def guides_dir() -> Path:
    """Return the absolute path to the guides directory."""
    return root() / "space" / "prompts" / "guide"


def guide_path(name: str) -> Path:
    """Return absolute path to a guide file."""
    return guides_dir() / name


def constitutions_dir() -> Path:
    """Return the absolute path to the constitutions directory."""
    return root() / "constitutions"


def resolve_constitution_path(value: str) -> Path:
    """Resolve a constitution path from config entry."""
    expanded = Path(value).expanduser()

    if expanded.is_absolute():
        return expanded

    parts = list(expanded.parts)
    if parts and parts[0] == "constitutions":
        parts = parts[1:]

    relative = Path(*parts) if parts else Path(expanded.name)
    return (constitutions_dir() / relative).resolve()

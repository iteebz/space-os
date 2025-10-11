from pathlib import Path


def workspace_root() -> Path:
    """Project root directory - crawls up to find .space/ or uses cwd."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".space").exists():
            return current
        current = current.parent
    return Path.cwd()


def space_root() -> Path:
    """Returns .space/ directory - crawls up from pwd, falls back to ~/.space."""
    current = Path.cwd()
    while current != current.parent:
        space_dir = current / ".space"
        if space_dir.exists():
            return space_dir
        current = current.parent
    return Path.home() / ".space"


def package_root() -> Path:
    """Returns space package root directory."""
    return Path(__file__).resolve().parent.parent


def constitution(filename: str) -> Path:
    """Returns the full path to a constitution file."""
    return package_root() / "constitutions" / filename


def canon_path() -> Path:
    """Returns path to human's canonical values."""
    return space_root() / "canon.md"

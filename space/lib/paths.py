from pathlib import Path


def workspace_root() -> Path:
    """Project root directory."""
    return Path.cwd()


def space_root() -> Path:
    """Returns .space/ directory in workspace."""
    return workspace_root() / ".space"


def package_root() -> Path:
    """Returns space package root directory."""
    return Path(__file__).resolve().parent.parent


def constitution(filename: str) -> Path:
    """Returns the full path to a constitution file."""
    return package_root() / "constitutions" / filename


def canon_path() -> Path:
    """Returns path to human's canonical values."""
    return space_root() / "canon.md"

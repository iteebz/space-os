from pathlib import Path


def registry_dir() -> Path:
    return Path.home() / ".space" / "registry"


def registry_db() -> Path:
    return registry_dir() / "registry.db"

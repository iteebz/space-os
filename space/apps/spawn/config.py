from pathlib import Path


def register_dir() -> Path:
    return Path.home() / ".space" / "register"


def register_db() -> Path:
    return register_dir() / "register.db"

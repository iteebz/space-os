from .. import config, storage, utils


def get_instructions() -> str:
    """Load current default instructions from file."""
    if not config.INSTRUCTIONS_FILE.exists():
        raise FileNotFoundError(f"Instructions file missing: {config.INSTRUCTIONS_FILE}")
    return config.INSTRUCTIONS_FILE.read_text()


def channel_instructions(channel_id: str) -> tuple[str, str, str] | None:
    """Get the locked instructions for a specific channel."""
    return storage.get_channel_instructions(channel_id)


def check_instructions():
    """Validate instructions file exists before channel operations."""
    if not config.INSTRUCTIONS_FILE.exists():
        raise RuntimeError(f"Required instructions file missing: {config.INSTRUCTIONS_FILE}")


def hash_instructions(content: str) -> str:
    """Generate 8-char hash for instruction content."""
    return utils.hash_content(content)

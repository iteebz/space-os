"""Symlink management for agent CLI shortcuts."""

import subprocess
from pathlib import Path


def _setup_launch_symlink(launch_script: Path) -> bool:
    """Setup launch script in ~/.local/bin. Called by space init."""
    try:
        bin_dir = Path.home() / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        symlink_path = bin_dir / "launch"
        subprocess.run(
            ["ln", "-sf", str(launch_script), str(symlink_path)],
            check=True,
            capture_output=True,
        )
        return True
    except Exception:
        return False


def create_agent_symlink(identity: str) -> bool:
    """Create symlink in ~/.local/bin for agent identity.

    Returns True if successful, False otherwise.
    """
    try:
        bin_dir = Path.home() / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        symlink_path = bin_dir / identity
        launch_executable = Path.home() / ".local" / "bin" / "launch"

        if not launch_executable.exists():
            return False

        subprocess.run(
            ["ln", "-sf", str(launch_executable), str(symlink_path)],
            check=True,
            capture_output=True,
        )
        return True
    except Exception:
        return False

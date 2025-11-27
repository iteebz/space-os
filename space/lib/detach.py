"""Fire-and-forget subprocess that outlives parent."""

import subprocess
import sys


def detach(args: list[str], cwd: str | None = None) -> None:
    """Spawn process that survives parent exit."""
    subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        cwd=cwd,
    )


def detach_python(module: str, *args: str, cwd: str | None = None) -> None:
    """Spawn Python module that survives parent exit."""
    detach([sys.executable, "-m", module, *args], cwd=cwd)

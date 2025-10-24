import subprocess
import sys


def _run_launch(role: str, agent: str):
    """Helper to call the spawn launch command."""
    try:
        subprocess.run(
            ["poetry", "run", "spawn", "launch", role, "--agent", agent],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(
            "Error: 'poetry' command not found. Is poetry installed and in your PATH?",
            file=sys.stderr,
        )
        sys.exit(1)


def gemini():
    _run_launch(role="harbinger", agent="gemini")


def claude():
    _run_launch(role="zealot", agent="claude")


def codex():
    _run_launch(role="sentinel", agent="codex")

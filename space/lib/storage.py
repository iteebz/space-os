from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path


def root() -> Path:
    """Return the workspace root that owns the spawn project.

    Prefer the directory the user invoked Spawn from when it already
    contains this project, so agents inherit the caller's context. Fall back
    to repository markers when the invocation directory is unrelated.
    """

    current = Path.cwd()

    # Prefer the first directory in the cwd->root chain that exposes the
    # workspace anchors we expect (`AGENTS.md` today). This avoids trapping the
    # runtime inside `private/spawn` when the invocation happens there.
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").exists():
            return candidate

    # This is a bit of a hack, but it's the best we can do for now.
    # We need to find the root of the project, but we can't rely on
    # the current working directory, because it might be different
    # from the project root.
    # So, we search for a file that is likely to be at the root of
    # the project, and then we go up from there.
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent

    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent

    return Path.cwd()


SPACE_DIR = root() / ".space"


def database_path(name: str) -> Path:
    """Return absolute path to a database file under the workspace .space directory."""
    path = SPACE_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_database(
    name: str, initializer: Callable[[sqlite3.Connection], None] | None = None
) -> Path:
    """Create database if missing and run optional initializer inside a transaction."""
    path = database_path(name)
    with sqlite3.connect(path) as conn:
        if initializer is not None:
            initializer(conn)
        conn.commit()
    return path


@contextmanager
def connect(name: str) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the named database, creating the file if required."""
    path = database_path(name)
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()

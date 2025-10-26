from pathlib import Path

import typer

from space.core import chats, spawn
from space.lib import paths, store


def init_default_agents():
    """Agents are now registered via spawn register. Explicit, no magic."""
    pass


def init():
    """Initialize space workspace structure and databases."""
    root = paths.space_root()

    paths.space_data().mkdir(parents=True, exist_ok=True)
    paths.canon_path().mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)

    with spawn.db.connect():
        pass
    with chats.db.connect():
        pass
    with store.ensure("bridge"):
        pass
    with store.ensure("memory"):
        pass
    with store.ensure("knowledge"):
        pass
    with store.ensure("events"):
        pass

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo(f"✓ User data at {Path.home() / '.space'}")

    init_default_agents()

    typer.echo()
    typer.echo("  ~/space/")
    typer.echo("    ├── canon/      → your persistent context (edit here)")
    typer.echo("    └── (code)")
    typer.echo()
    typer.echo("  ~/.space/")
    typer.echo("    ├── data/       → runtime databases")
    typer.echo("    └── backups/    → snapshots")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  space wake --as <identity>")

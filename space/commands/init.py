from pathlib import Path

import typer

from space.os.core import spawn
from space.os.lib import db, paths


def init():
    """Initialize space workspace structure and databases."""
    root = paths.space_root()

    paths.space_data().mkdir(parents=True, exist_ok=True)
    paths.canon_path().mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)

    with spawn.connect():
        pass
    with db.ensure("bridge"):
        pass
    with db.ensure("memory"):
        pass
    with db.ensure("knowledge"):
        pass
    with db.ensure("events"):
        pass

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo(f"✓ User data at {Path.home() / '.space'}")
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

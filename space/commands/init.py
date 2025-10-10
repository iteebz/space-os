import typer

from .. import bridge, knowledge, memory
from ..lib import paths
from ..spawn import registry


def init():
    """Initialize space workspace structure and databases."""
    root = paths.workspace_root()

    (root / ".space").mkdir(parents=True, exist_ok=True)
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)

    registry.init_db()
    bridge.db._connect().close()
    memory.db.connect().close()
    knowledge.db.connect().close()

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo("  .space/     → infrastructure")
    typer.echo("  canon/      → human context")
    typer.echo("  projects/   → active work")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  space wake --as <identity>")

import typer

from space.os import bridge, knowledge, memory
from space.os.lib import paths
from space.os.spawn import registry


def init():
    """Initialize space workspace structure and databases."""
    root = paths.space_root()

    paths.dot_space().mkdir(parents=True, exist_ok=True)
    paths.canon_path().mkdir(parents=True, exist_ok=True)
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

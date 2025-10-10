import typer

from ..bridge import db as bridge_db
from ..knowledge import db as knowledge_db
from ..lib.db import workspace_root
from ..memory import db as memory_db
from ..spawn import registry as spawn_registry


def init():
    """Initialize space workspace structure and databases."""
    root = workspace_root()

    (root / ".space").mkdir(parents=True, exist_ok=True)
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)

    spawn_registry.init_db()
    bridge_db._ensure_db()
    memory_db.connect().close()
    knowledge_db.connect().close()

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo("  .space/     → infrastructure")
    typer.echo("  canon/      → human context")
    typer.echo("  projects/   → active work")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  space wake --as <identity>")

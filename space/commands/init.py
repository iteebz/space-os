import typer

from ..lib.db import workspace_root
from ..spawn import registry as spawn_registry
from ..bridge import db as bridge_db
from ..memory import db as memory_db
from ..knowledge import db as knowledge_db


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
    typer.echo(f"  .space/     → infrastructure")
    typer.echo(f"  canon/      → human context")
    typer.echo(f"  projects/   → active work")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  spawn list")
    typer.echo("  memory --as <identity>")

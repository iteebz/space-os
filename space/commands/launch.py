"""Launch guide for new space-os users."""

import typer
from pathlib import Path

from space.os.lib import paths

def launch():
    """Display the space-os launch guide (hitchhiker's manual)."""
    guide_path = Path.home() / "space" / "LAUNCH.md"
    
    if not guide_path.exists():
        typer.echo("Launch guide not found at ~/space/LAUNCH.md", err=True)
        raise typer.Exit(code=1)
    
    with open(guide_path) as f:
        typer.echo(f.read())

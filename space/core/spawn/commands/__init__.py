"""Spawn commands: CLI parsing & typer wiring."""

import typer

from space.lib import errors

from . import agents, tasks

errors.install_error_handler("spawn")

app = typer.Typer()

app.add_typer(agents.app)
app.add_typer(tasks.app)

__all__ = ["agents", "tasks", "app"]

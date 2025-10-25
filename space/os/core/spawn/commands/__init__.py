"""Spawn commands: CLI parsing & typer wiring."""

import typer

from space.os.lib import errors

from . import agents, tasks

errors.install_error_handler("spawn")

app = typer.Typer()

__all__ = ["agents", "tasks", "app"]

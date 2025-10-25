"""Knowledge commands: CLI parsing & typer wiring."""

import typer

from space.os.lib import errors

errors.install_error_handler("knowledge")

app = typer.Typer()


def __getattr__(name):
    if name == "entries":
        from . import entries

        return entries
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["entries", "app"]

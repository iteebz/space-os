"""Memory commands."""

import typer

from space.os.lib import errors

errors.install_error_handler("memory")

app = typer.Typer()


def __getattr__(name):
    if name == "entries":
        from . import entries

        return entries
    if name == "summary":
        from . import summary

        return summary
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["entries", "summary", "app"]

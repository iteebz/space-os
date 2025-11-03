"""Trace CLI: unified execution introspection."""

import typer

from space.apps.trace import api
from space.apps.trace.formatting import (
    display_agent_trace,
    display_channel_trace,
    display_session_trace,
)

app = typer.Typer(invoke_without_command=True, no_args_is_help=False, add_completion=False)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context, query: str = typer.Argument(None)):
    """Trace execution: agent spawns, session context, or channel activity.

    Query syntax:
    - Explicit: agent:zealot, session:7a6a07de, channel:general (recommended)
    - Implicit: zealot, 7a6a07de, general (auto-inferred)
    """
    if ctx.invoked_subcommand is not None:
        return

    if query is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)

    try:
        result = api.trace(query)
    except ValueError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1) from e

    if result["type"] == "identity":
        display_agent_trace(result)
    elif result["type"] == "session":
        display_session_trace(result)
    elif result["type"] == "channel":
        display_channel_trace(result)


def main() -> None:
    """Entry point for trace command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


__all__ = ["app", "main"]

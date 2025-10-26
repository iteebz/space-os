"""Unified concept retrieval: evolution + current state."""

import typer

from space.apps.context.lib import api
from space.lib import display, errors, output, readme

errors.install_error_handler("context")

context = typer.Typer(invoke_without_command=True)


@context.callback()
def main_command(
    ctx: typer.Context,
    query: str | None = typer.Argument(None, help="Query to retrieve context for"),
    identity: str | None = typer.Option(None, "--as", help="Scope to identity (default: all)"),
    all_agents: bool = typer.Option(False, "--all", help="Cross-agent perspective"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    """Unified context retrieval: trace evolution + current state."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if help:
        typer.echo(readme.load("context"))
        ctx.exit()

    if (ctx.resilient_parsing or ctx.invoked_subcommand is None) and not query:
        typer.echo(readme.load("context"))
        return

    timeline = api.collect_timeline(query, identity, all_agents)
    current_state = api.collect_current_state(query, identity, all_agents)

    if ctx.obj.get("json_output"):
        typer.echo(
            output.out_json(
                {
                    "evolution": timeline,
                    "state": current_state,
                }
            )
        )
        return

    if ctx.obj.get("quiet_output"):
        return

    display.display_context(timeline, current_state)

    if not timeline and not any(current_state.values()):
        output.out_text(f"No context found for '{query}'", ctx.obj)


def main() -> None:
    """Entry point for poetry script."""
    context()

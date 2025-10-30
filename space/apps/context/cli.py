"""Unified concept retrieval: evolution + current state."""

import typer

from space.apps.context import api
from space.lib import display, errors, output

errors.install_error_handler("context")

app = typer.Typer(invoke_without_command=True)


@app.command(name="")  # This makes it the default command when no subcommand is given
def context_main_command(
    ctx: typer.Context,
    query: str | None = typer.Argument(None, help="Query to retrieve context for"),
    all_agents: bool = typer.Option(False, "--all", help="Cross-agent perspective"),
):
    """Unified context retrieval: trace evolution + current state."""
    # The common options (identity, json_output, quiet_output) are now handled by add_common_options
    # and are available in ctx.obj

    # This check is now simpler as common options are handled by the callback
    if (ctx.resilient_parsing or ctx.invoked_subcommand is not None) and not query:
        typer.echo("context [query] --as <identity>: Retrieve concept evolution and current state.")
        return

    # Retrieve identity from ctx.obj
    identity = ctx.obj.get("identity")
    json_output = ctx.obj.get("json")
    quiet_output = ctx.obj.get("quiet")

    timeline = api.collect_timeline(query, identity, all_agents)
    current_state = api.collect_current_state(query, identity, all_agents)

    if json_output:
        typer.echo(
            output.out_json(
                {
                    "evolution": timeline,
                    "state": current_state,
                }
            )
        )
        return

    if quiet_output:
        return

    display.display_context(timeline, current_state)

    if not timeline and not any(current_state.values()):
        output.out_text(f"No context found for '{query}'", ctx.obj)

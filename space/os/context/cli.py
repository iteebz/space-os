"""Unified concept retrieval: evolution + current state."""

from typing import Annotated

import typer

from space.apps.context.api import collect_current_state, collect_timeline
from space.cli import output
from space.os.context import display

app = typer.Typer(add_completion=False)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Query to search")],
    identity: Annotated[str | None, typer.Option("--as", help="Agent identity to use.")] = None,
    scope: Annotated[
        str,
        typer.Option("--scope", help="Search scope: memory|knowledge|canon|bridge|sessions|all"),
    ] = "all",
    all_agents: Annotated[
        bool, typer.Option("--all", help="Include all agents' memories (requires --as)")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output in JSON format.")
    ] = False,
    quiet_output: Annotated[
        bool, typer.Option("--quiet", "-q", help="Suppress non-essential output.")
    ] = False,
) -> None:
    """Search unified context across memory, knowledge, canon, bridge, and sessions.

    Examples:
      context search "pause"                             # Search all sources for "pause"
      context search "my observations" --as agent        # Search agent's private memory
      context search "architecture" --scope knowledge    # Search knowledge domain only

    Scope options: all (default), memory, knowledge, canon, bridge, sessions
    """
    if scope != "all" and scope not in ("memory", "knowledge", "canon", "bridge", "sessions"):
        typer.echo(
            f"Error: Invalid scope '{scope}'. Use: all, memory, knowledge, canon, bridge, sessions"
        )
        raise typer.Exit(1)

    timeline = collect_timeline(query, identity, all_agents)
    current_state = collect_current_state(query, identity, all_agents)

    if scope != "all":
        timeline = [item for item in timeline if item["source"].lower() == scope.lower()]
        current_state = {scope: current_state.get(scope, [])}

    if json_output:
        typer.echo(
            output.out_json(
                {
                    "query": query,
                    "scope": scope,
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
        typer.echo(f"No context found for '{query}'")


def main() -> None:
    """Entry point for context command."""
    app()


if __name__ == "__main__":
    main()

"""Unified concept retrieval: evolution + current state."""

from typing import Annotated

import typer

from space.apps.context.api import collect_current_state, collect_timeline
from space.lib import argv, errors, output
from space.os.context import display

errors.install_error_handler("context")

argv.flex_args("as")

app = typer.Typer(
    invoke_without_command=True,
    add_completion=False,
    help="Unified context retrieval across memory, knowledge, bridge, provider chats, and canon (git-backed docs).",
)


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    identity: Annotated[str | None, typer.Option("--as", help="Agent identity to use.")] = None,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output in JSON format.")
    ] = False,
    quiet_output: Annotated[
        bool, typer.Option("--quiet", "-q", help="Suppress non-essential output.")
    ] = False,
):
    output.set_flags(ctx, json_output, quiet_output)

    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj["identity"] = identity
    ctx.obj["json"] = json_output
    ctx.obj["quiet"] = quiet_output

    if ctx.resilient_parsing:
        return

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command(name="")
def search(
    ctx: typer.Context,
    query: str | None = typer.Argument(None, help="Query to search"),
    scope: str = typer.Option("all", "--scope", help="Search scope: memory|knowledge|canon|all"),
    all_agents: bool = typer.Option(
        False, "--all", help="Include all agents' memories (requires --as)"
    ),
):
    """Search unified context across memory, knowledge, canon, and bridge.

    Examples:
      context search "Redis caching"              # Search all public sources
      context search "my observations" --as agent # Search agent's private memory
      context search architecture/caching --scope knowledge  # Search domain

    Scope options: all (default), memory, knowledge, canon, bridge
    Timeline shows evolution. State groups results by source.
    """
    if not query:
        typer.echo(ctx.get_help())
        return

    identity = ctx.obj.get("identity")
    json_output = ctx.obj.get("json")
    quiet_output = ctx.obj.get("quiet")

    if scope != "all" and scope not in ("memory", "knowledge", "canon", "bridge"):
        raise typer.BadParameter(
            f"Invalid scope: {scope}. Use: all, memory, knowledge, canon, bridge"
        )

    timeline = collect_timeline(query, identity, all_agents)
    current_state = collect_current_state(query, identity, all_agents)

    if scope != "all":
        timeline = [item for item in timeline if item["source"].lower().startswith(scope.lower())]
        scope_map = {
            "memory": "memory",
            "knowledge": "knowledge",
            "canon": "canon",
            "bridge": "bridge",
        }
        if scope in scope_map:
            current_state = {scope_map[scope]: current_state.get(scope_map[scope], [])}
        else:
            current_state = {}

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
        output.out_text(f"No context found for '{query}'", ctx.obj)


def main() -> None:
    """Entry point for context command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e

"""Unified concept retrieval: evolution + current state."""

from typing import Annotated

import typer

from space.lib import display, errors, output
from space.os.context.api import collect_current_state, collect_timeline

errors.install_error_handler("context")

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
    query: str | None = typer.Argument(None, help="Query to search (required)"),
    all_agents: bool = typer.Option(
        False, "--all", help="Include all agents' memories (requires --as <identity>)"
    ),
):
    """Search unified context across knowledge, bridge, chats, and canon (shared/public sources).

    Memory is private per agent. To search an agent's memory: context --as <identity> "query"
    To search multiple agents' memories: context --as <identity> --all "query"

    Timeline shows evolution (10 most recent). State groups results by source.
    """
    if not query:
        typer.echo(ctx.get_help())
        return

    identity = ctx.obj.get("identity")
    json_output = ctx.obj.get("json")
    quiet_output = ctx.obj.get("quiet")

    timeline = collect_timeline(query, identity, all_agents)
    current_state = collect_current_state(query, identity, all_agents)

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


def main() -> None:
    """Entry point for context command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e

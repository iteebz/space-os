from typing import Annotated

import typer

from space.lib import output
from space.lib.format import format_memory_entries
from space.os.memory.ops import namespace as ops_namespace


def create_namespace_cli(namespace: str, noun: str) -> typer.Typer:
    """Creates a Typer app for a memory namespace."""
    app = typer.Typer(
        name=namespace,
        help=f"""Manage {noun} entries.

Use `memory {namespace} "<message>" --as <agent>` to quickly add a {noun} entry.
Use `memory {namespace} --as <agent>` to list {noun} entries.""",
    )

    @app.callback(invoke_without_command=True)
    def callback(
        ctx: typer.Context,
    ):
        # Ensure ctx.obj is a dict, and initialize if not present
        if ctx.obj is None:
            ctx.obj = {}

        if "identity" not in ctx.obj:
            typer.echo("Error: Agent identity must be provided via --as option.", err=True)
            raise typer.Exit(1)

        # Default to listing if no subcommand is invoked
        if ctx.invoked_subcommand is None:
            ops_namespace.list_entries(ctx, namespace, False)  # Default to not showing all

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        all: Annotated[bool, typer.Option("--all", help="Include archived entries.")] = False,
        json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
        quiet: Annotated[bool, typer.Option("--quiet", help="Suppress output.")] = False,
    ):
        if ctx.obj is None or "identity" not in ctx.obj:
            typer.echo("Error: Agent identity must be provided via --as option.", err=True)
            raise typer.Exit(1)
        ctx.obj["all"] = all
        ctx.obj["json"] = json
        ctx.obj["quiet"] = quiet
        entries = ops_namespace.list_entries(ctx, namespace, show_all=all)
        if json:
            output.json_output([entry.model_dump() for entry in entries])
        elif not quiet:
            output.out_text(format_memory_entries(entries), ctx.obj)

    @app.command("add")
    def add_command(
        ctx: typer.Context,
        message: Annotated[str, typer.Argument(help=f"Message to add to the {noun}.")],
        json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
        quiet: Annotated[bool, typer.Option("--quiet", help="Suppress output.")] = False,
    ):
        if ctx.obj is None or "identity" not in ctx.obj:
            typer.echo("Error: Agent identity must be provided via --as option.", err=True)
            raise typer.Exit(1)
        ctx.obj["json"] = json
        ctx.obj["quiet"] = quiet
        entry = ops_namespace.add_entry(ctx, namespace, message)
        if json:
            output.json_output(entry.model_dump_json())
        elif not quiet:
            typer.echo(f"Added {namespace} entry: {entry.uuid}")

    return app

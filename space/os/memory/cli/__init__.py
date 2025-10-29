"""Memory commands."""

from typing import Annotated

import typer

from space.lib import errors, output

from . import entries  # Keep existing entries for now
from .namespace import create_namespace_cli  # Import the factory

errors.install_error_handler("memory")


app = typer.Typer(
    invoke_without_command=True,
    help="""Memory: Knowledge Base Management.

Use `memory <namespace> <message> --as <agent>` to quickly add entries to specific namespaces.
Example: `memory journal "Wound down session" --as zealot`

Use `memory <namespace> --as <agent>` to list entries in a namespace.
Example: `memory notes --as zealot`

For general memory commands (add, list, archive, core, replace, inspect), use `memory <command> ...`
Example: `memory add --topic general "A general thought" --as zealot`""",
)


# Register commands from entries.py
entries.register_commands(app)

# Dynamically create and add namespace apps
app.add_typer(create_namespace_cli("journal", "journal"), name="journal")
app.add_typer(create_namespace_cli("notes", "note"), name="notes")
app.add_typer(create_namespace_cli("tasks", "task"), name="tasks")
app.add_typer(create_namespace_cli("beliefs", "belief"), name="beliefs")


@app.callback()
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
        if identity:
            # Invoke the 'list' command from entries.py using ctx.invoke
            # This ensures Typer handles the context and argument passing correctly.
            ctx.invoke(entries.list, ident=identity, topic=None, show_all=True, raw_output=False)
        else:
            typer.echo("memory [command] --as <identity>: Store and retrieve agent memories.")
            typer.echo("Run 'memory --help' for a list of commands.")


__all__ = ["app"]

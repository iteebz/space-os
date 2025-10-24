import sys

import typer

from space.os.lib import errors, readme

from . import entries

errors.install_error_handler("memory")

memory = typer.Typer(invoke_without_command=True)
memory.command(name="add")(entries.add)
memory.command(name="edit")(entries.edit)
memory.command(name="list")(entries.list)
memory.command(name="search")(entries.search)
memory.command(name="archive")(entries.archive)
memory.command(name="core")(entries.core)
memory.command(name="inspect")(entries.inspect)
memory.command(name="replace")(entries.replace)
memory.command(name="summary")(entries.summary)


@memory.callback()
def cb(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Identity name"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    from space.os.lib import output

    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["identity"] = identity

    if help:
        typer.echo(readme.load("memory"))
        ctx.exit()

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        if identity:
            entries._list_entries(identity, ctx, include_archived=show_all)
        else:
            typer.echo(readme.load("memory"))


def main() -> None:
    """Entry point for poetry script."""
    try:
        memory()
    except typer.Exit as e:
        if e.exit_code and e.exit_code != 0:
            from space.os import events

            cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(no command)"
            events.emit("cli", "error", data=f"memory {cmd}")
        sys.exit(e.exit_code)
    except Exception as e:
        from space.os import events

        cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(no command)"
        events.emit("cli", "error", data=f"memory {cmd}: {str(e)}")
        sys.exit(1)


__all__ = ["memory"]

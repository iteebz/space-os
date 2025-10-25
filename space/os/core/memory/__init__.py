import sys

import typer

from space.os.lib import errors, output, readme

from . import api, commands, db
from .api import (
    add_entry,
    add_link,
    archive_entry,
    clear_entries,
    delete_entry,
    edit_entry,
    find_related,
    get_by_memory_id,
    get_by_uuid,
    get_chain,
    get_core_entries,
    get_memories,
    get_recent_entries,
    get_summary,
    mark_core,
    replace_entry,
    restore_entry,
    search_entries,
    update_summary,
)

errors.install_error_handler("memory")

db.register()


memory = typer.Typer(invoke_without_command=True)
memory.add_typer(commands.app)


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
            commands.entries._list_entries(identity, ctx, include_archived=show_all)
        else:
            typer.echo(readme.load("memory"))


def main() -> None:
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


__all__ = [
    "memory",
    "api",
    "db",
    "add_entry",
    "add_link",
    "archive_entry",
    "clear_entries",
    "delete_entry",
    "edit_entry",
    "find_related",
    "get_by_memory_id",
    "get_by_uuid",
    "get_chain",
    "get_core_entries",
    "get_memories",
    "get_recent_entries",
    "get_summary",
    "mark_core",
    "replace_entry",
    "restore_entry",
    "search_entries",
    "update_summary",
]

"""Memory CLI: Knowledge Base Management."""

from dataclasses import asdict
from typing import Annotated

import typer

from space.lib import display, errors, output
from space.lib.format import format_memory_entries
from space.os import spawn
from space.os.memory import api
from space.os.memory.ops import namespace as ops_namespace

errors.install_error_handler("memory")


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
        if ctx.obj is None:
            ctx.obj = {}

        if "identity" not in ctx.obj:
            typer.echo("Error: Agent identity must be provided via --as option.", err=True)
            raise typer.Exit(1)

        if ctx.invoked_subcommand is None:
            ops_namespace.list_entries(ctx, namespace, False)

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


main_app = typer.Typer(
    invoke_without_command=True,
    help="""Memory: Knowledge Base Management.

Use `memory <namespace> <message> --as <agent>` to quickly add entries to specific namespaces.
Example: `memory journal "Wound down session" --as zealot`

Use `memory <namespace> --as <agent>` to list entries in a namespace.
Example: `memory notes --as zealot`

For general memory commands (add, list, archive, core, replace, inspect), use `memory <command> ...`
Example: `memory add --topic general "A general thought" --as zealot`""",
)


@main_app.callback()
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
            ctx.invoke(list, ident=identity, topic=None, show_all=True, raw_output=False)
        else:
            typer.echo("memory [command] --as <identity>: Store and retrieve agent memories.")
            typer.echo("Run 'memory --help' for a list of commands.")


@main_app.command("add")
def add(
    ctx: typer.Context,
    message: str = typer.Argument(..., help="The memory message"),
    topic: str = typer.Option(..., help="Topic name"),
):
    """Add a new memory entry."""
    ident = ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    agent = spawn.get_agent(ident)
    if not agent:
        raise typer.BadParameter(f"Identity '{ident}' not registered.")
    agent_id = agent.agent_id
    entry_id = api.add_entry(agent_id, topic, message)
    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"entry_id": entry_id}))
    else:
        output.out_text(f"Added memory: {topic}", ctx.obj)


@main_app.command("edit")
def edit(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to edit"),
    message: str = typer.Argument(..., help="The new message content"),
):
    """Edit an existing memory entry."""
    entry = api.get_by_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        api.edit_entry(uuid, message)
        output.out_text(f"Edited {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("memory", entry.agent_id, "edit", e)
        raise typer.BadParameter(str(e)) from e


@main_app.command("list")
def list(
    ctx: typer.Context,
    ident: str = typer.Option(None, "--identity"),
    topic: str = typer.Option(None, help="Topic name"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
    raw_output: bool = typer.Option(
        False, "--raw", help="Output raw timestamps instead of humanized."
    ),
):
    """List memory entries for an identity and optional topic."""
    identity = ident or ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")
    try:
        entries = api.list_entries(identity, topic, show_all=show_all)
    except ValueError as e:
        output.emit_error("memory", None, "list", e)
        raise typer.BadParameter(str(e)) from e

    entries.sort(key=lambda e: (not e.core, e.timestamp), reverse=True)
    if not entries:
        output.out_text("No entries", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(e) for e in entries]))
    else:
        output.out_text(format_memory_entries(entries, raw_output=raw_output), ctx.obj)
        if not ctx.obj.get("quiet_output"):
            display.show_context(identity)


@main_app.command("archive")
def archive(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to archive"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived entry"),
):
    """Archive or restore a memory entry."""
    entry = api.get_by_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        if restore:
            api.restore_entry(uuid)
            action = "restored"
        else:
            api.archive_entry(uuid)
            action = "archived"
        output.out_text(f"{action} {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("memory", entry.agent_id, "archive/restore", e)
        raise typer.BadParameter(str(e)) from e


@main_app.command("core")
def core(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to mark/unmark as core"),
    unmark: bool = typer.Option(False, "--unmark", help="Unmark as core"),
):
    """Mark or unmark entry as core memory."""
    entry = api.get_by_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        is_core = not unmark
        api.mark_core(uuid, core=is_core)
        output.out_text(f"{'★' if is_core else ''} {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("memory", entry.agent_id, "core", e)
        raise typer.BadParameter(str(e)) from e


@main_app.command("inspect")
def inspect(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to inspect"),
    limit: int = typer.Option(5, help="Number of related entries to show"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
):
    """Inspect entry and find related nodes via keyword similarity."""
    identity_name = ctx.obj.get("identity")
    if not identity_name:
        raise typer.BadParameter("--as required")
    agent = spawn.get_agent(identity_name)
    if not agent:
        raise typer.BadParameter(f"Identity '{identity_name}' not registered.")
    agent_id = agent.agent_id
    try:
        entry = api.get_by_id(uuid)
    except ValueError as e:
        output.emit_error("memory", agent_id, "inspect", e)
        raise typer.BadParameter(str(e)) from e

    if not entry:
        output.out_text("Not found", ctx.obj)
        return

    if entry.agent_id != agent_id:
        agent = spawn.get_agent(entry.agent_id)
        name = agent.identity if agent else entry.agent_id
        output.out_text(f"Belongs to {name}", ctx.obj)
        return

    related = api.find_related(entry, limit=limit, show_all=show_all)
    if ctx.obj.get("json_output"):
        payload = {
            "entry": asdict(entry),
            "related": [{"entry": asdict(r[0]), "overlap": r[1]} for r in related],
        }
        typer.echo(output.out_json(payload))
    else:
        display.show_memory_entry(entry, ctx.obj, related=related)


@main_app.command("replace")
def replace(
    ctx: typer.Context,
    old_id: str = typer.Argument(None, help="Single UUID to replace"),
    message: str = typer.Argument(..., help="New message content"),
    supersedes: str = typer.Option(None, help="Comma-separated UUIDs to replace"),
    note: str = typer.Option("", "--note", help="Synthesis note"),
):
    """Replace memory entry with new version, archiving old and linking both."""
    id = ctx.obj.get("identity")
    if not id:
        raise typer.BadParameter("--as required")
    agent = spawn.get_agent(id)
    if not agent:
        raise typer.BadParameter(f"Identity '{id}' not registered.")
    agent_id = agent.agent_id

    if supersedes:
        old_ids = [x.strip() for x in supersedes.split(",")]
    elif old_id:
        old_ids = [old_id]
    else:
        raise typer.BadParameter("Provide old_id or --supersedes")

    old_entry = api.get_by_id(old_ids[0])
    if not old_entry:
        raise typer.BadParameter(f"Not found: {old_ids[0]}")

    new_uuid = api.replace_entry(old_ids, agent_id, old_entry.topic, message, note)
    output.out_text(f"Merged {len(old_ids)} → {new_uuid[-8:]}", ctx.obj)


main_app.add_typer(create_namespace_cli("journal", "journal"), name="journal")
main_app.add_typer(create_namespace_cli("notes", "note"), name="notes")
main_app.add_typer(create_namespace_cli("tasks", "task"), name="tasks")
main_app.add_typer(create_namespace_cli("beliefs", "belief"), name="beliefs")


def main() -> None:
    """Entry point for poetry script."""
    try:
        main_app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


app = main_app

__all__ = ["app", "main"]

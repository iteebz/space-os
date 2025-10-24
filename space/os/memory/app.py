import sys
from dataclasses import asdict

import typer

from space.os import events
from space.os.lib import errors, output, readme
from space.os.spawn import registry

from ..lib import display
from ..lib import identity as identity_lib
from ..lib.format import format_memory_entries
from . import db

errors.install_error_handler("memory")

app = typer.Typer(invoke_without_command=True)


def _list_entries(identity: str, ctx, include_archived: bool = False, raw_output: bool = False):
    try:
        entries = db.get_memories(identity, None, include_archived=include_archived)
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


@app.callback()
def main_command(
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
            _list_entries(identity, ctx, include_archived=show_all)
        else:
            typer.echo(readme.load("memory"))


@app.command("add")
def add_entry_command(
    ctx: typer.Context,
    message: str = typer.Argument(..., help="The memory message"),
    identity: str = typer.Option(None, "--as", help="Identity name"),
    topic: str = typer.Option(..., help="Topic name"),
):
    """Add a new memory entry."""
    identity = identity or ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")
    agent_id = registry.ensure_agent(identity)
    entry_id = db.add_entry(agent_id, topic, message)
    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"entry_id": entry_id}))
    else:
        output.out_text(f"Added memory: {topic}", ctx.obj)


@app.command("edit")
def edit_entry_command(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to edit"),
    message: str = typer.Argument(..., help="The new message content"),
):
    """Edit an existing memory entry."""
    entry = db.get_by_memory_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        db.edit_entry(uuid, message)
        output.out_text(f"Edited {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("memory", entry.agent_id, "edit", e)
        raise typer.BadParameter(str(e)) from e


@app.command("summary")
def summary_command(
    ctx: typer.Context,
    message: str = typer.Argument(
        None, help="The summary message. If provided, adds/replaces the summary."
    ),
    identity: str = typer.Option(None, "--as", help="Identity name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """Add, replace, or list summary entries for an identity."""
    identity = identity or ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")
    agent_id = registry.ensure_agent(identity)

    if message:
        existing = db.get_memories(identity, topic="summary", limit=1)
        if existing:
            old_entry = existing[0]
            new_uuid = db.replace_entry(
                [old_entry.memory_id], agent_id, "summary", message, "CLI summary update"
            )
            output.out_text(f"Updated summary {new_uuid[-8:]}", ctx.obj)
        else:
            entry_id = db.add_entry(agent_id, "summary", message)
            output.out_text(f"Added summary {entry_id[-8:]}", ctx.obj)
    else:
        entries = db.get_memories(identity, topic="summary", limit=1)
        if not entries:
            output.out_text("No summary found", ctx.obj)
            return

        if ctx.obj.get("json_output"):
            typer.echo(output.out_json(asdict(entries[0])))
        else:
            output.out_text(f"CURRENT: [summary] {entries[0].message}", ctx.obj)
            chain = db.get_chain(entries[0].memory_id)
            if chain["predecessors"]:
                output.out_text("SUPERSEDES:", ctx.obj)
                for p in chain["predecessors"]:
                    output.out_text(f"  [{p.memory_id[-8:]}] {p.message}", ctx.obj)


@app.command("list")
def list_entries_command(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Identity name"),
    topic: str = typer.Option(None, help="Topic name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
    raw_output: bool = typer.Option(
        False, "--raw", help="Output raw timestamps instead of humanized."
    ),
):
    """List memory entries for an identity and optional topic."""
    identity = identity or ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")
    try:
        entries = db.get_memories(identity, topic, include_archived=include_archived or show_all)
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


@app.command("archive")
def archive_entry_command(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to archive"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived entry"),
):
    """Archive or restore a memory entry."""
    entry = db.get_by_memory_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        if restore:
            db.restore_entry(uuid)
            action = "restored"
        else:
            db.archive_entry(uuid)
            action = "archived"
        output.out_text(f"{action} {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("memory", entry.agent_id, "archive/restore", e)
        raise typer.BadParameter(str(e)) from e


@app.command("search")
def search_entries_command(
    ctx: typer.Context,
    keyword: str = typer.Argument(..., help="Keyword to search"),
    identity: str = typer.Option(None, "--as", help="Identity name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """Search memory entries by keyword."""
    identity = identity or ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")
    entries = db.search_entries(identity, keyword, include_archived=include_archived)

    if not entries:
        output.out_text("No results", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(e) for e in entries]))
        return

    output.out_text(f"Found {len(entries)} for '{keyword}'\n", ctx.obj)
    topic = None
    for e in entries:
        if e.topic != topic:
            if topic is not None:
                typer.echo()
            output.out_text(f"# {e.topic}", ctx.obj)
            topic = e.topic
        mark = " [ARCHIVED]" if e.archived_at else ""
        output.out_text(f"[{e.memory_id[-8:]}] {e.message}{mark}", ctx.obj)


@app.command("core")
def mark_core_command(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to mark/unmark as core"),
    unmark: bool = typer.Option(False, "--unmark", help="Unmark as core"),
):
    """Mark or unmark entry as core memory."""
    entry = db.get_by_memory_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        is_core = not unmark
        db.mark_core(uuid, core=is_core)
        output.out_text(f"{'★' if is_core else ''} {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("memory", entry.agent_id, "core", e)
        raise typer.BadParameter(str(e)) from e


@app.command("inspect")
def inspect_entry_command(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to inspect"),
    identity: str = typer.Option(None, "--as", help="Identity name"),
    limit: int = typer.Option(5, help="Number of related entries to show"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived in related"),
):
    """Inspect entry and find related nodes via keyword similarity."""
    identity = identity or ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")
    agent_id = registry.ensure_agent(identity)
    try:
        entry = db.get_by_uuid(uuid)
    except ValueError as e:
        output.emit_error("memory", agent_id, "inspect", e)
        raise typer.BadParameter(str(e)) from e

    if not entry:
        output.out_text("Not found", ctx.obj)
        return

    if entry.agent_id != agent_id:
        output.out_text(f"Belongs to {registry.get_identity(entry.agent_id)}", ctx.obj)
        return

    related = db.find_related(entry, limit=limit, include_archived=include_archived)
    if ctx.obj.get("json_output"):
        payload = {
            "entry": asdict(entry),
            "related": [{"entry": asdict(r[0]), "overlap": r[1]} for r in related],
        }
        typer.echo(output.out_json(payload))
    else:
        display.show_memory_entry(entry, ctx.obj, related=related)


@app.command("replace")
def replace_entry_command(
    ctx: typer.Context,
    old_id: str = typer.Argument(None, help="Single UUID to replace"),
    message: str = typer.Argument(..., help="New message content"),
    identity: str = typer.Option(None, "--as", help="Identity name"),
    supersedes: str = typer.Option(None, help="Comma-separated UUIDs to replace"),
    note: str = typer.Option("", "--note", help="Synthesis note"),
):
    """Replace memory entry with new version, archiving old and linking both."""
    identity = identity or ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")
    identity_lib.constitute_identity(identity)
    agent_id = registry.ensure_agent(identity)

    if supersedes:
        old_ids = [x.strip() for x in supersedes.split(",")]
    elif old_id:
        old_ids = [old_id]
    else:
        raise typer.BadParameter("Provide old_id or --supersedes")

    old_entry = db.get_by_uuid(old_ids[0])
    if not old_entry:
        raise typer.BadParameter(f"Not found: {old_ids[0]}")

    new_uuid = db.replace_entry(old_ids, agent_id, old_entry.topic, message, note)
    output.out_text(f"Merged {len(old_ids)} → {new_uuid[-8:]}", ctx.obj)


def main() -> None:
    """Entry point for poetry script."""
    try:
        app()
    except typer.Exit as e:
        if e.exit_code and e.exit_code != 0:
            cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(no command)"
            events.emit("cli", "error", data=f"memory {cmd}")
        sys.exit(e.exit_code)
    except Exception as e:
        cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(no command)"
        events.emit("cli", "error", data=f"memory {cmd}: {str(e)}")
        sys.exit(1)

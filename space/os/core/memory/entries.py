from dataclasses import asdict

import typer

from space.os.core.spawn import db as spawn_db
from space.os.lib import display, errors, identity, output
from space.os.lib.format import format_memory_entries

from . import db

errors.install_error_handler("memory")


def _list_entries(id: str, ctx, include_archived: bool = False, raw_output: bool = False):
    try:
        entries = db.get_memories(id, None, include_archived=include_archived)
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
            display.show_context(id)


def add(
    ctx: typer.Context,
    message: str = typer.Argument(..., help="The memory message"),
    ident: str = typer.Option(None, "--as", help="Identity name"),
    topic: str = typer.Option(..., help="Topic name"),
):
    """Add a new memory entry."""
    ident = ident or ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    agent_id = spawn_db.ensure_agent(ident)
    entry_id = db.add_entry(agent_id, topic, message)
    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"entry_id": entry_id}))
    else:
        output.out_text(f"Added memory: {topic}", ctx.obj)


def edit(
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


def list(
    ctx: typer.Context,
    ident: str = typer.Option(None, "--as", help="Identity name"),
    topic: str = typer.Option(None, help="Topic name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
    raw_output: bool = typer.Option(
        False, "--raw", help="Output raw timestamps instead of humanized."
    ),
):
    """List memory entries for an identity and optional topic."""
    ident = ident or ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    try:
        entries = db.get_memories(ident, topic, include_archived=include_archived or show_all)
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
            display.show_context(ident)


def search(
    ctx: typer.Context,
    keyword: str = typer.Argument(..., help="Keyword to search"),
    ident: str = typer.Option(None, "--as", help="Identity name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """Search memory entries by keyword."""
    ident = ident or ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    entries = db.search_entries(ident, keyword, include_archived=include_archived)

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


def archive(
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


def core(
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


def inspect(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to inspect"),
    identity_name: str = typer.Option(None, "--as", help="Identity name"),
    limit: int = typer.Option(5, help="Number of related entries to show"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived in related"),
):
    """Inspect entry and find related nodes via keyword similarity."""
    identity_name = identity_name or ctx.obj.get("identity")
    if not identity_name:
        raise typer.BadParameter("--as required")
    agent_id = spawn_db.ensure_agent(identity_name)
    try:
        entry = db.get_by_uuid(uuid)
    except ValueError as e:
        output.emit_error("memory", agent_id, "inspect", e)
        raise typer.BadParameter(str(e)) from e

    if not entry:
        output.out_text("Not found", ctx.obj)
        return

    if entry.agent_id != agent_id:
        output.out_text(f"Belongs to {spawn_db.get_agent_name(entry.agent_id)}", ctx.obj)
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


def replace(
    ctx: typer.Context,
    old_id: str = typer.Argument(None, help="Single UUID to replace"),
    message: str = typer.Argument(..., help="New message content"),
    id: str = typer.Option(None, "--as", help="Identity name"),
    supersedes: str = typer.Option(None, help="Comma-separated UUIDs to replace"),
    note: str = typer.Option("", "--note", help="Synthesis note"),
):
    """Replace memory entry with new version, archiving old and linking both."""
    id = id or ctx.obj.get("identity")
    if not id:
        raise typer.BadParameter("--as required")
    identity.constitute_identity(id)
    agent_id = spawn_db.ensure_agent(id)

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


def summary(
    ctx: typer.Context,
    message: str = typer.Argument(
        None, help="The summary message. If provided, adds/replaces the summary."
    ),
    ident: str = typer.Option(None, "--as", help="Identity name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """Add, replace, or list summary entries for an identity."""
    ident = ident or ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    agent_id = spawn_db.ensure_agent(ident)

    if message:
        existing = db.get_memories(ident, topic="summary", limit=1)
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
        entries = db.get_memories(ident, topic="summary", limit=1)
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

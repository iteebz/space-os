import sys
from dataclasses import asdict

import typer

from space import events, readme
from space.lib import cli_utils, errors
from space.spawn import registry

from ..lib import display
from ..lib import identity as identity_lib
from . import db

errors.install_error_handler("memory")

app = typer.Typer(invoke_without_command=True)


@app.callback()
def main_command(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Identity name"),
    archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    cli_utils.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.update({"identity": identity, "archived": archived})
    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        if not identity:
            typer.echo(readme.load("memory"))
        else:
            list_entries_command(
                ctx,
                identity=identity_lib.require_identity(ctx, identity),
                topic=None,
                include_archived=archived,
                show_all=False,
                raw_output=False,
            )


@app.command("add")
def add_entry_command(
    ctx: typer.Context,
    message: str = typer.Argument(..., help="The memory message"),
    identity: str = typer.Option(None, "--as", help="Identity name"),
    topic: str = typer.Option(..., help="Topic name"),
):
    """Add a new memory entry."""
    resolved_identity = identity_lib.require_identity(ctx, identity)
    agent_id = registry.ensure_agent(resolved_identity)
    entry_id = db.add_entry(agent_id, topic, message)
    if ctx.obj.get("json_output"):
        typer.echo(
            cli_utils.out_json(
                {"entry_id": entry_id, "identity": resolved_identity, "topic": topic}
            )
        )
    else:
        cli_utils.out_text(f"Added memory for {resolved_identity} on topic {topic}", ctx.obj)


@app.command("edit")
def edit_entry_command(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to edit"),
    message: str = typer.Argument(..., help="The new message content"),
):
    """Edit an existing memory entry."""
    entry = db.get_by_memory_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry with UUID '{uuid}' not found.")

    try:
        db.edit_entry(uuid, message)
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"uuid": uuid, "status": "edited"}))
        else:
            cli_utils.out_text(f"Edited entry {uuid}", ctx.obj)
    except ValueError as e:
        cli_utils.emit_error("memory", entry.agent_id, "edit", e)
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"uuid": uuid, "status": "error", "message": str(e)}))
        else:
            raise typer.BadParameter(str(e)) from e


@app.command("delete")
def delete_entry_command(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to delete"),
):
    """Delete a memory entry."""
    entry = db.get_by_memory_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry with UUID '{uuid}' not found.")

    try:
        db.delete_entry(uuid)
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"uuid": uuid, "status": "deleted"}))
        else:
            cli_utils.out_text(f"Deleted entry {uuid}", ctx.obj)
    except ValueError as e:
        cli_utils.emit_error("memory", entry.agent_id, "delete", e)
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"uuid": uuid, "status": "error", "message": str(e)}))
        else:
            raise typer.BadParameter(str(e)) from e


@app.command("clear")
def clear_entries_command(
    ctx: typer.Context,
    identity: str = typer.Option(..., "--as", help="Identity name"),
    topic: str = typer.Option(None, help="Topic name"),
):
    """Clear memory entries for an identity and optional topic."""
    resolved_identity = identity_lib.require_identity(None, identity)
    agent_id = registry.ensure_agent(resolved_identity)
    try:
        db.clear_entries(resolved_identity, topic)
        scope = f"topic '{topic}'" if topic else "all topics"
        if ctx.obj.get("json_output"):
            typer.echo(
                cli_utils.out_json({"identity": identity, "topic": topic, "status": "cleared"})
            )
        else:
            cli_utils.out_text(f"Cleared {scope} for {identity}", ctx.obj)
    except ValueError as e:
        cli_utils.emit_error("memory", agent_id, "clear", e)
        if ctx.obj.get("json_output"):
            typer.echo(
                cli_utils.out_json(
                    {"identity": identity, "topic": topic, "status": "error", "message": str(e)}
                )
            )
        else:
            raise typer.BadParameter(str(e)) from e


@app.command("summary")
def summary_command(
    ctx: typer.Context,
    message: str = typer.Argument(
        None, help="The summary message. If provided, adds/replaces the summary."
    ),
    identity: str = typer.Option(..., "--as", help="Identity name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """Add, replace, or list summary entries for an identity."""
    resolved_identity = identity_lib.require_identity(ctx, identity)
    agent_id = registry.ensure_agent(resolved_identity)

    if message:
        existing_summaries = db.get_memories(resolved_identity, topic="summary", limit=1)
        if existing_summaries:
            old_entry = existing_summaries[0]
            new_uuid = db.replace_entry(
                [old_entry.memory_id], agent_id, "summary", message, "CLI summary update"
            )
            if ctx.obj.get("json_output"):
                typer.echo(
                    cli_utils.out_json({"new_uuid": new_uuid, "supersedes": [old_entry.memory_id]})
                )
            else:
                cli_utils.out_text(
                    f"Updated summary (appended to {len(existing_summaries)} entries) with new ID {new_uuid[-8:]}",
                    ctx.obj,
                )
        else:
            entry_id = db.add_entry(agent_id, "summary", message)
            if ctx.obj.get("json_output"):
                typer.echo(
                    cli_utils.out_json(
                        {"entry_id": entry_id, "identity": resolved_identity, "topic": "summary"}
                    )
                )
            else:
                cli_utils.out_text(f"Added summary for {resolved_identity}.", ctx.obj)
    else:
        entries = db.get_memories(resolved_identity, topic="summary", limit=1)
        if not entries:
            if ctx.obj.get("json_output"):
                typer.echo(cli_utils.out_json([]))
            else:
                cli_utils.out_text(f"No summary found for {resolved_identity}.", ctx.obj)
            return

        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json(asdict(entries[0])))
        else:
            cli_utils.out_text(f"CURRENT: [summary] {entries[0].message}", ctx.obj)
            chain = db.get_chain(entries[0].memory_id)
            if chain["predecessors"]:
                cli_utils.out_text("SUPERSEDES:", ctx.obj)
                for p in chain["predecessors"]:
                    cli_utils.out_text(f"  [{p.memory_id[-8:]}] {p.message}", ctx.obj)


@app.command("list")
def list_entries_command(
    ctx: typer.Context,
    identity: str = typer.Option(..., "--as", help="Identity name"),
    topic: str = typer.Option(None, help="Topic name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries (bypass smart defaults)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    raw_output: bool = typer.Option(
        False, "--raw", help="Output raw timestamps instead of humanized."
    ),
):
    """List memory entries for an identity and optional topic."""
    if ctx.obj is None:
        ctx.obj = {}
    resolved_identity = identity_lib.require_identity(ctx, identity)
    use_json = ctx.obj.get("json_output", json_output)
    ctx.obj.get("quiet_output", quiet_output)

    try:
        entries = db.get_memories(resolved_identity, topic, include_archived=include_archived)
    except ValueError as e:
        cli_utils.emit_error("memory", None, "list", e)
        if use_json:
            typer.echo(
                cli_utils.out_json(
                    {
                        "identity": resolved_identity,
                        "topic": topic,
                        "status": "error",
                        "message": str(e),
                    }
                )
            )
        else:
            raise typer.BadParameter(str(e)) from e
        return

    entries.sort(key=lambda e: (not e.core, e.timestamp), reverse=True)
    if not entries:
        scope = f"topic '{topic}'" if topic else "all topics"
        if use_json:
            typer.echo(cli_utils.out_json([]))
        else:
            cli_utils.out_text(f"No entries found for {identity} in {scope}", ctx.obj)
        return

    if use_json:
        typer.echo(cli_utils.out_json([asdict(e) for e in entries]))
    else:
        cli_utils.out_text(display.format_memory_entries(entries, raw_output=raw_output), ctx.obj)
        if not (quiet_output or ctx.obj.get("quiet_output")):
            display.show_context(resolved_identity)


@app.command("archive")
def archive_entry_command(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to archive"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived entry"),
):
    """Archive or restore a memory entry."""
    entry = db.get_by_memory_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry with UUID '{uuid}' not found.")

    try:
        if restore:
            db.restore_entry(uuid)
            action = "restored"
        else:
            db.archive_entry(uuid)
            action = "archived"

        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"uuid": uuid, "status": action}))
        else:
            cli_utils.out_text(f"{action.capitalize()} entry {uuid}", ctx.obj)
    except ValueError as e:
        cli_utils.emit_error("memory", entry.agent_id, "archive/restore", e)
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"uuid": uuid, "status": "error", "message": str(e)}))
        else:
            raise typer.BadParameter(str(e)) from e


@app.command("search")
def search_entries_command(
    ctx: typer.Context,
    keyword: str = typer.Argument(..., help="Keyword to search"),
    identity: str = typer.Option(..., "--as", help="Identity name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """Search memory entries by keyword."""
    entries = db.search_entries(identity, keyword, include_archived=include_archived)

    if not entries:
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json([]))
        else:
            cli_utils.out_text(f"No entries found for '{keyword}'", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(cli_utils.out_json([asdict(e) for e in entries]))
    else:
        cli_utils.out_text(f"Found {len(entries)} entries for '{keyword}':\n", ctx.obj)
        current_topic = None
        for e in entries:
            if e.topic != current_topic:
                if current_topic is not None:
                    typer.echo()
                cli_utils.out_text(f"# {e.topic}", ctx.obj)
                current_topic = e.topic
            archived_mark = " [ARCHIVED]" if e.archived_at else ""
            cli_utils.out_text(
                f"[{e.memory_id[-8:]}] [{e.timestamp}] {e.message}{archived_mark}", ctx.obj
            )


@app.command("core")
def mark_core_command(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to mark/unmark as core"),
    unmark: bool = typer.Option(False, "--unmark", help="Unmark as core"),
):
    """Mark or unmark entry as core memory."""
    entry = db.get_by_memory_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry with UUID '{uuid}' not found.")

    try:
        db.mark_core(uuid, core=not unmark)
        action = "unmarked" if unmark else "marked"
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"uuid": uuid, "core": not unmark}))
        else:
            cli_utils.out_text(f"{action.capitalize()} {uuid} as core", ctx.obj)
    except ValueError as e:
        cli_utils.emit_error("memory", entry.agent_id, "core", e)
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"uuid": uuid, "error": str(e)}))
        else:
            raise typer.BadParameter(str(e)) from e


@app.command("inspect")
def inspect_entry_command(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to inspect"),
    identity: str = typer.Option(..., "--as", help="Identity name"),
    limit: int = typer.Option(5, help="Number of related entries to show"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived in related"),
):
    """Inspect entry and find related nodes via keyword similarity."""
    resolved_agent_id = registry.ensure_agent(identity)

    try:
        entry = db.get_by_uuid(uuid)
    except ValueError as e:
        cli_utils.emit_error("memory", resolved_agent_id, "inspect", e)
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"uuid": uuid, "error": str(e)}))
        else:
            raise typer.BadParameter(str(e)) from e
        return

    if not entry:
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json(None))
        else:
            cli_utils.out_text(f"No entry found with UUID '{uuid}'", ctx.obj)
        return

    if entry.agent_id != resolved_agent_id:
        if ctx.obj.get("json_output"):
            typer.echo(cli_utils.out_json({"error": "Entry belongs to different identity"}))
        else:
            cli_utils.out_text(
                f"Entry belongs to {registry.get_identity(entry.agent_id)}, not {identity}", ctx.obj
            )
        return

    related = db.find_related(entry, limit=limit, include_archived=include_archived)

    if ctx.obj.get("json_output"):
        payload = {
            "entry": asdict(entry),
            "related": [{"entry": asdict(r[0]), "overlap": r[1]} for r in related],
        }
        typer.echo(cli_utils.out_json(payload))
    else:
        archived_mark = " [ARCHIVED]" if entry.archived_at else ""
        core_mark = " ★" if entry.core else ""
        cli_utils.out_text(
            f"[{entry.memory_id[-8:]}] {entry.topic} by {registry.get_identity(entry.agent_id)}{archived_mark}{core_mark}",
            ctx.obj,
        )
        cli_utils.out_text(f"Created: {entry.timestamp}\n", ctx.obj)
        cli_utils.out_text(f"{entry.message}\n", ctx.obj)

        if related:
            cli_utils.out_text("─" * 60, ctx.obj)
            cli_utils.out_text(f"Related nodes ({len(related)}):\n", ctx.obj)
            for rel_entry, overlap in related:
                archived_mark = " [ARCHIVED]" if rel_entry.archived_at else ""
                core_mark = " ★" if rel_entry.core else ""
                cli_utils.out_text(
                    f"[{rel_entry.memory_id[-8:]}] {rel_entry.topic} ({overlap} keywords){archived_mark}{core_mark}",
                    ctx.obj,
                )
                cli_utils.out_text(
                    f"  {rel_entry.message[:100]}{'...' if len(rel_entry.message) > 100 else ''}\n",
                    ctx.obj,
                )


@app.command("replace")
def replace_entry_command(
    ctx: typer.Context,
    old_id: str = typer.Argument(None, help="Single UUID to replace"),
    message: str = typer.Argument(..., help="New message content"),
    identity: str = typer.Option(..., "--as", help="Identity name"),
    supersedes: str = typer.Option(None, help="Comma-separated UUIDs to replace (for multi-merge)"),
    note: str = typer.Option("", "--note", help="Synthesis note explaining the change"),
):
    """Replace memory entry with new version, archiving old and linking both."""
    identity_lib.constitute_identity(identity)
    agent_id = registry.ensure_agent(identity)

    if supersedes:
        old_ids = [x.strip() for x in supersedes.split(",")]
    elif old_id:
        old_ids = [old_id]
    else:
        raise typer.BadParameter("Must provide either old_id or --supersedes")

    old_entry = db.get_by_uuid(old_ids[0])
    if not old_entry:
        raise typer.BadParameter(f"Entry not found: {old_ids[0]}")

    new_uuid = db.replace_entry(old_ids, agent_id, old_entry.topic, message, note)

    if ctx.obj.get("json_output"):
        typer.echo(cli_utils.out_json({"new_uuid": new_uuid, "supersedes": old_ids}))
    else:
        cli_utils.out_text(f"Replaced {len(old_ids)} entry(ies) with {new_uuid[-8:]}", ctx.obj)


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

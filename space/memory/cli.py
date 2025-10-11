import json
from dataclasses import asdict

import typer

from space.spawn import registry

from ..lib import identity as identity_lib
from ..lib import readme
from . import db
from .display import show_context, show_smart_memory

app = typer.Typer(invoke_without_command=True)


@app.callback()
def main_command(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Identity name"),
    archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    ctx.obj = {"identity": identity, "archived": archived}
    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        if not identity:
            try:
                protocol_content = readme.load("memory")
                typer.echo(protocol_content)
            except (FileNotFoundError, ValueError) as e:
                typer.echo(f"❌ memory README not found: {e}")
        else:
            list_entries_command(
                identity=identity,
                topic=None,
                json_output=False,
                quiet_output=False,
                include_archived=archived,
                show_all=False,
            )


@app.command("add")
def add_entry_command(
    ctx: typer.Context,
    message: str = typer.Argument(..., help="The memory message"),
    identity: str = typer.Option(None, "--as", help="Identity name"),
    topic: str = typer.Option(..., help="Topic name"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Add a new memory entry."""
    resolved_identity = identity_lib.require_identity(ctx, identity)
    agent_id = registry.ensure_agent(resolved_identity)
    entry_id = db.add_entry(agent_id, topic, message)
    if json_output:
        typer.echo(
            json.dumps({"entry_id": entry_id, "identity": resolved_identity, "topic": topic})
        )
    elif not quiet_output:
        typer.echo(f"Added memory for {resolved_identity} on topic {topic}")


@app.command("edit")
def edit_entry_command(
    uuid: str = typer.Argument(..., help="UUID of the entry to edit"),
    message: str = typer.Argument(..., help="The new message content"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Edit an existing memory entry."""
    try:
        db.edit_entry(uuid, message)
        if json_output:
            typer.echo(json.dumps({"uuid": uuid, "status": "edited"}))
        elif not quiet_output:
            typer.echo(f"Edited entry {uuid}")
    except ValueError as e:
        if json_output:
            typer.echo(json.dumps({"uuid": uuid, "status": "error", "message": str(e)}))
        else:
            raise typer.BadParameter(str(e)) from e


@app.command("delete")
def delete_entry_command(
    uuid: str = typer.Argument(..., help="UUID of the entry to delete"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Delete a memory entry."""
    try:
        db.delete_entry(uuid)
        if json_output:
            typer.echo(json.dumps({"uuid": uuid, "status": "deleted"}))
        elif not quiet_output:
            typer.echo(f"Deleted entry {uuid}")
    except ValueError as e:
        if json_output:
            typer.echo(json.dumps({"uuid": uuid, "status": "error", "message": str(e)}))
        else:
            raise typer.BadParameter(str(e)) from e


@app.command("clear")
def clear_entries_command(
    identity: str = typer.Option(..., "--as", help="Identity name"),
    topic: str = typer.Option(None, help="Topic name"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Clear memory entries for an identity and optional topic."""
    db.clear_entries(identity, topic)
    scope = f"topic '{topic}'" if topic else "all topics"
    if json_output:
        typer.echo(json.dumps({"identity": identity, "topic": topic, "status": "cleared"}))
    elif not quiet_output:
        typer.echo(f"Cleared {scope} for {identity}")


@app.command("list")
def list_entries_command(
    identity: str = typer.Option(..., "--as", help="Identity name"),
    topic: str = typer.Option(None, help="Topic name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries (bypass smart defaults)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """List memory entries for an identity and optional topic."""
    identity_lib.constitute_identity(identity)

    if topic or show_all:
        entries = db.get_entries(identity, topic, include_archived=include_archived)
        if not entries:
            scope = f"topic '{topic}'" if topic else "all topics"
            if json_output:
                typer.echo(json.dumps([]))
            elif not quiet_output:
                typer.echo(f"No entries found for {identity} in {scope}")
            return

        if json_output:
            typer.echo(json.dumps([asdict(e) for e in entries], indent=2))
        elif not quiet_output:
            current_topic = None
            for e in entries:
                if e.topic != current_topic:
                    if current_topic is not None:
                        typer.echo()
                    typer.echo(f"# {e.topic}")
                    current_topic = e.topic
                core_mark = " ★" if e.core else ""
                typer.echo(f"[{e.uuid[-8:]}] [{e.timestamp}] {e.message}{core_mark}")

            show_context(identity)
    else:
        show_smart_memory(identity, json_output, quiet_output)


@app.command("archive")
def archive_entry_command(
    uuid: str = typer.Argument(..., help="UUID of the entry to archive"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived entry"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Archive or restore a memory entry."""
    try:
        if restore:
            db.restore_entry(uuid)
            action = "restored"
        else:
            db.archive_entry(uuid)
            action = "archived"

        if json_output:
            typer.echo(json.dumps({"uuid": uuid, "status": action}))
        elif not quiet_output:
            typer.echo(f"{action.capitalize()} entry {uuid}")
    except ValueError as e:
        if json_output:
            typer.echo(json.dumps({"uuid": uuid, "status": "error", "message": str(e)}))
        else:
            raise typer.BadParameter(str(e)) from e


@app.command("search")
def search_entries_command(
    keyword: str = typer.Argument(..., help="Keyword to search"),
    identity: str = typer.Option(..., "--as", help="Identity name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Search memory entries by keyword."""
    entries = db.search_entries(identity, keyword, include_archived=include_archived)

    if not entries:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo(f"No entries found for '{keyword}'")
        return

    if json_output:
        typer.echo(json.dumps([asdict(e) for e in entries], indent=2))
    elif not quiet_output:
        typer.echo(f"Found {len(entries)} entries for '{keyword}':\n")
        current_topic = None
        for e in entries:
            if e.topic != current_topic:
                if current_topic is not None:
                    typer.echo()
                typer.echo(f"# {e.topic}")
                current_topic = e.topic
            archived_mark = " [ARCHIVED]" if e.archived_at else ""
            typer.echo(f"[{e.uuid[-8:]}] [{e.timestamp}] {e.message}{archived_mark}")


@app.command("core")
def mark_core_command(
    uuid: str = typer.Argument(..., help="UUID of the entry to mark/unmark as core"),
    unmark: bool = typer.Option(False, "--unmark", help="Unmark as core"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Mark or unmark entry as core memory."""
    try:
        db.mark_core(uuid, core=not unmark)
        action = "unmarked" if unmark else "marked"
        if json_output:
            typer.echo(json.dumps({"uuid": uuid, "core": not unmark}))
        elif not quiet_output:
            typer.echo(f"{action.capitalize()} {uuid} as core")
    except ValueError as e:
        if json_output:
            typer.echo(json.dumps({"uuid": uuid, "error": str(e)}))
        else:
            raise typer.BadParameter(str(e)) from e


@app.command("inspect")
def inspect_entry_command(
    uuid: str = typer.Argument(..., help="UUID of the entry to inspect"),
    identity: str = typer.Option(..., "--as", help="Identity name"),
    limit: int = typer.Option(5, help="Number of related entries to show"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived in related"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Inspect entry and find related nodes via keyword similarity."""
    entry = db.get_by_uuid(uuid)
    if not entry:
        if json_output:
            typer.echo(json.dumps(None))
        elif not quiet_output:
            typer.echo(f"No entry found with UUID '{uuid}'")
        return

    if entry.identity != identity:
        if json_output:
            typer.echo(json.dumps({"error": "Entry belongs to different identity"}))
        elif not quiet_output:
            typer.echo(f"Entry belongs to {entry.identity}, not {identity}")
        return

    related = db.find_related(entry, limit=limit, include_archived=include_archived)

    if json_output:
        payload = {
            "entry": asdict(entry),
            "related": [{"entry": asdict(r[0]), "overlap": r[1]} for r in related],
        }
        typer.echo(json.dumps(payload))
    elif not quiet_output:
        archived_mark = " [ARCHIVED]" if entry.archived_at else ""
        core_mark = " ★" if entry.core else ""
        typer.echo(
            f"[{entry.uuid[-8:]}] {entry.topic} by {entry.identity}{archived_mark}{core_mark}"
        )
        typer.echo(f"Created: {entry.timestamp}\n")
        typer.echo(f"{entry.message}\n")

        if related:
            typer.echo("─" * 60)
            typer.echo(f"Related nodes ({len(related)}):\n")
            for rel_entry, overlap in related:
                archived_mark = " [ARCHIVED]" if rel_entry.archived_at else ""
                core_mark = " ★" if rel_entry.core else ""
                typer.echo(
                    f"[{rel_entry.uuid[-8:]}] {rel_entry.topic} ({overlap} keywords){archived_mark}{core_mark}"
                )
                typer.echo(
                    f"  {rel_entry.message[:100]}{'...' if len(rel_entry.message) > 100 else ''}\n"
                )


def main() -> None:
    """Entry point for poetry script."""
    app()

import json
from dataclasses import asdict

import typer

from ..knowledge import db as knowledge_db
from ..lib import lattice
from ..spawn import registry as spawn_registry
from . import db

app = typer.Typer(invoke_without_command=True)

# Removed: PROTOCOL_FILE definitions and protocols.track calls
# Removed: show_dashboard functions


@app.callback()
def main_command(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Identity name"),
    archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    ctx.obj = {"archived": archived}
    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        if not identity:
            try:
                protocol_content = lattice.load("### memory")
                typer.echo(protocol_content)
            except (FileNotFoundError, ValueError) as e:
                typer.echo(f"❌ memory section not found in README: {e}")
        else:
            ctx.invoke(
                list_entries_command,
                identity=identity,
                topic=None,
                json_output=False,
                quiet_output=False,
                include_archived=archived,
            )


@app.command("add")
def add_entry_command(
    identity: str = typer.Option(..., "--as", help="Identity name"),
    topic: str = typer.Option(..., help="Topic name"),
    message: str = typer.Argument(..., help="The memory message"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Add a new memory entry."""
    entry_id = db.add_entry(identity, topic, message)
    if json_output:
        typer.echo(json.dumps({"entry_id": entry_id, "identity": identity, "topic": topic}))
    elif not quiet_output:
        typer.echo(f"Added memory for {identity} on topic {topic}")


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
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """List memory entries for an identity and optional topic."""
    _constitute_identity(identity)
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
            typer.echo(f"[{e.uuid[-8:]}] [{e.timestamp}] {e.message}")

        _show_context(identity)


def _constitute_identity(identity: str):
    """Hash constitution and emit provenance event."""
    from .. import events
    from ..spawn import registry, spawn

    role = _extract_role(identity)
    if not role:
        return

    try:
        registry.init_db()
        cfg = spawn.load_config()
        if role not in cfg["roles"]:
            return

        const_path = spawn.get_constitution_path(role)
        base_constitution = const_path.read_text()
        full_identity = spawn.inject_identity(base_constitution, identity)
        const_hash = spawn.hash_content(full_identity)
        registry.save_constitution(const_hash, full_identity)
        
        model = _extract_model_from_identity(identity)
        events.emit(
            "memory",
            "constitution_invoked",
            identity,
            json.dumps({"constitution_hash": const_hash, "role": role, "model": model}),
        )
    except (FileNotFoundError, ValueError):
        pass


def _extract_role(identity: str) -> str | None:
    """Extract role from identity like zealot-1 -> zealot."""
    if "-" in identity:
        return identity.rsplit("-", 1)[0]
    return identity


def _extract_model_from_identity(identity: str) -> str | None:
    """Extract model name from spawn config based on identity."""
    from ..spawn import spawn
    
    role = _extract_role(identity)
    if not role:
        return None
    
    try:
        cfg = spawn.load_config()
        if role in cfg["roles"]:
            base_identity = cfg["roles"][role].get("base_identity")
            if base_identity and "agents" in cfg:
                agent_cfg = cfg["agents"].get(base_identity, {})
                return agent_cfg.get("model")
    except (FileNotFoundError, ValueError, KeyError):
        pass
    
    return None


def _show_context(identity: str):
    typer.echo("\n" + "─" * 60)

    regs = spawn_registry.list_registrations()
    my_regs = [r for r in regs if r.sender_id == identity]
    if my_regs:
        topics = {r.topic for r in my_regs}
        typer.echo(f"\nREGISTERED: {', '.join(sorted(topics))}")

    knowledge_entries = knowledge_db.query_by_contributor(identity)
    if knowledge_entries:
        domains = {e.domain for e in knowledge_entries}
        typer.echo(
            f"\nKNOWLEDGE: {len(knowledge_entries)} entries across {', '.join(sorted(domains))}"
        )

    typer.echo("\n" + "─" * 60)


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
            "related": [{"entry": asdict(r[0]), "overlap": r[1]} for r in related]
        }
        typer.echo(json.dumps(payload))
    elif not quiet_output:
        archived_mark = " [ARCHIVED]" if entry.archived_at else ""
        typer.echo(f"[{entry.uuid[-8:]}] {entry.topic} by {entry.identity}{archived_mark}")
        typer.echo(f"Created: {entry.timestamp}\n")
        typer.echo(f"{entry.message}\n")
        
        if related:
            typer.echo("─" * 60)
            typer.echo(f"Related nodes ({len(related)}):\n")
            for rel_entry, overlap in related:
                archived_mark = " [ARCHIVED]" if rel_entry.archived_at else ""
                typer.echo(f"[{rel_entry.uuid[-8:]}] {rel_entry.topic} ({overlap} keywords){archived_mark}")
                typer.echo(f"  {rel_entry.message[:100]}{'...' if len(rel_entry.message) > 100 else ''}\n")


def main() -> None:
    """Entry point for poetry script."""
    app()

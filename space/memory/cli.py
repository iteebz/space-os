import json
from dataclasses import asdict

import typer

from ..bridge import db as bridge_db
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
):
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
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """List memory entries for an identity and optional topic."""
    _constitute_identity(identity)
    entries = db.get_entries(identity, topic)
    if not entries:
        scope = f"topic '{topic}'" if topic else "all topics"
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo(f"No entries found for {identity} in {scope}")
        return

    if json_output:
        typer.echo(json.dumps([asdict(e) for e in entries]))
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
    """Hash and save constitution on boot."""
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
        registry.save_agent_identity(identity, full_identity, const_hash)
    except (FileNotFoundError, ValueError):
        pass


def _extract_role(identity: str) -> str | None:
    """Extract role from identity like zealot-1 -> zealot."""
    if "-" in identity:
        return identity.rsplit("-", 1)[0]
    return identity


def _show_context(identity: str):
    typer.echo("\n" + "─" * 60)

    channels = bridge_db.fetch_channels(agent_id=identity)
    unread = [c for c in channels if c.unread_count > 0]

    if unread:
        typer.echo("\nBRIDGE INBOX:")
        for c in unread:
            msgs = bridge_db.get_new_messages(bridge_db.get_channel_id(c.name), identity)
            last_sender = msgs[-1].sender if msgs else "unknown"
            typer.echo(f"  {c.name}: {c.unread_count} unread (last: {last_sender})")

    active = [c.name for c in channels if c.unread_count > 0 or c.last_activity]
    if active:
        typer.echo(f"\nACTIVE CHANNELS: {', '.join(active[:5])}")

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
    typer.echo(f"\n» memory --as {identity} --topic <topic>")
    typer.echo(f"» bridge recv <channel> --as {identity}")


def main() -> None:
    """Entry point for poetry script."""
    app()

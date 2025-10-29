"""Entry commands: add, edit, list, search, archive, core, inspect, replace."""

from dataclasses import asdict

import typer

from space.lib import display, output
from space.lib.format import format_memory_entries
from space.os import spawn

from .. import api


def register_commands(app: typer.Typer):
    @app.command("add")
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

    @app.command("edit")
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

    @app.command("list")
    def list(
        ctx: typer.Context,
        topic: str = typer.Option(None, help="Topic name"),
        show_all: bool = typer.Option(False, "--all", help="Show all entries"),
        raw_output: bool = typer.Option(
            False, "--raw", help="Output raw timestamps instead of humanized."
        ),
    ):
        """List memory entries for an identity and optional topic."""
        ident = ctx.obj.get("identity")
        if not ident:
            raise typer.BadParameter("--as required")
        try:
            entries = api.list_entries(ident, topic, show_all=show_all)
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

    @app.command("archive")
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

    @app.command("core")
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

    @app.command("inspect")
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

    @app.command("replace")
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

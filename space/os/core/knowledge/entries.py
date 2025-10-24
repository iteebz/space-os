from dataclasses import asdict

import typer

from space.os.core.spawn import db as spawn_db
from space.os.lib import errors, output

from . import db

errors.install_error_handler("knowledge")


def add(
    ctx: typer.Context,
    content: str = typer.Argument(..., help="The knowledge content"),
    domain: str = typer.Option(..., help="Domain of the knowledge"),
    contributor: str = typer.Option(..., "--as", help="Agent identity"),
    confidence: float = typer.Option(None, help="Confidence score (0.0-1.0)"),
):
    """Add a new knowledge entry."""
    agent_id = spawn_db.ensure_agent(contributor)
    entry_id = db.write_knowledge(domain, agent_id, content, confidence)
    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"entry_id": entry_id}))
    else:
        output.out_text(
            f"Added knowledge entry {entry_id} for domain '{domain}' by '{contributor}'", ctx.obj
        )


def list(
    ctx: typer.Context,
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """List all knowledge entries."""
    entries = db.list_all(include_archived=include_archived)
    if not entries:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json([]))
        else:
            output.out_text("No knowledge entries found.", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(entry) for entry in entries]))
    else:
        for entry in entries:
            agent_name = spawn_db.get_identity(entry.agent_id) or entry.agent_id
            output.out_text(
                f"[{entry.knowledge_id[-8:]}] [{entry.created_at}] Domain: {entry.domain}, "
                f"Agent: {agent_name}, Confidence: {entry.confidence or 'N/A'}\n"
                f"  Content: {entry.content[:100]}{'...' if len(entry.content) > 100 else ''}\n",
                ctx.obj,
            )


def query_by_domain(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain to query knowledge by"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """Query knowledge entries by domain."""
    entries = db.query_by_domain(domain, include_archived=include_archived)
    if not entries:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json([]))
        else:
            output.out_text(f"No knowledge entries found for domain '{domain}'.", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(entry) for entry in entries]))
    else:
        for entry in entries:
            agent_name = spawn_db.get_identity(entry.agent_id) or entry.agent_id
            output.out_text(
                f"[{entry.knowledge_id[-8:]}] [{entry.created_at}] Agent: {agent_name}, "
                f"Confidence: {entry.confidence or 'N/A'}\n"
                f"  Content: {entry.content[:100]}{'...' if len(entry.content) > 100 else ''}\n",
                ctx.obj,
            )


def query_by_agent(
    ctx: typer.Context,
    agent: str = typer.Argument(..., help="Agent to query knowledge by"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """Query knowledge entries by agent."""
    agent_id = spawn_db.get_agent_id(agent)
    if not agent_id:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json([]))
        else:
            output.out_text(f"Agent '{agent}' not found. Run `spawn` to list agents.", ctx.obj)
        return

    entries = db.query_by_agent(agent_id, include_archived=include_archived)
    if not entries:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json([]))
        else:
            output.out_text(f"No knowledge entries found for agent '{agent}'.", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(entry) for entry in entries]))
    else:
        for entry in entries:
            output.out_text(
                f"[{entry.knowledge_id[-8:]}] [{entry.created_at}] Domain: {entry.domain}, "
                f"Confidence: {entry.confidence or 'N/A'}\n"
                f"  Content: {entry.content[:100]}{'...' if len(entry.content) > 100 else ''}\n",
                ctx.obj,
            )


def get(
    ctx: typer.Context,
    entry_id: str = typer.Argument(..., help="UUID of the knowledge entry"),
):
    """Get a knowledge entry by its UUID."""
    entry = db.get_by_id(entry_id)
    if not entry:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json(None))
        else:
            output.out_text(f"No knowledge entry found with ID '{entry_id}'.", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json(asdict(entry)))
    else:
        agent_name = spawn_db.get_identity(entry.agent_id) or entry.agent_id
        output.out_text(
            f"ID: {entry.knowledge_id}\n"
            f"Created At: {entry.created_at}\n"
            f"Domain: {entry.domain}\n"
            f"Agent: {agent_name}\n"
            f"Confidence: {entry.confidence or 'N/A'}\n"
            f"Content:\n{entry.content}\n",
            ctx.obj,
        )


def inspect(
    ctx: typer.Context,
    entry_id: str = typer.Argument(..., help="UUID of the knowledge entry"),
    limit: int = typer.Option(5, help="Number of related entries to show"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived in related"),
):
    """Inspect entry and find related nodes via keyword similarity."""
    entry = db.get_by_id(entry_id)
    if not entry:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json(None))
        else:
            output.out_text(f"No knowledge entry found with ID '{entry_id}'.", ctx.obj)
        return

    related = db.find_related(entry, limit=limit, include_archived=include_archived)

    if ctx.obj.get("json_output"):
        payload = {
            "entry": asdict(entry),
            "related": [{"entry": asdict(r[0]), "overlap": r[1]} for r in related],
        }
        typer.echo(output.out_json(payload))
    else:
        agent_name = spawn_db.get_identity(entry.agent_id) or entry.agent_id
        archived_mark = " [ARCHIVED]" if entry.archived_at else ""
        output.out_text(
            f"[{entry.knowledge_id[-8:]}] {entry.domain} by {agent_name}{archived_mark}", ctx.obj
        )
        output.out_text(f"Created: {entry.created_at}", ctx.obj)
        output.out_text(f"Confidence: {entry.confidence or 'N/A'}\n", ctx.obj)
        output.out_text(f"{entry.content}\n", ctx.obj)

        if related:
            output.out_text("─" * 60, ctx.obj)
            output.out_text(f"Related nodes ({len(related)}):\n", ctx.obj)
            for rel_entry, overlap in related:
                rel_agent_name = spawn_db.get_identity(rel_entry.agent_id) or rel_entry.agent_id
                archived_mark = " [ARCHIVED]" if rel_entry.archived_at else ""
                output.out_text(
                    f"[{rel_entry.knowledge_id[-8:]}] {rel_entry.domain} by {rel_agent_name} ({overlap} keywords){archived_mark}",
                    ctx.obj,
                )
                output.out_text(
                    f"  {rel_entry.content[:100]}{'...' if len(rel_entry.content) > 100 else ''}\n",
                    ctx.obj,
                )


def archive(
    ctx: typer.Context,
    entry_id: str = typer.Argument(..., help="UUID of the knowledge entry"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived entry"),
):
    """Archive or restore a knowledge entry."""
    if restore:
        db.restore_entry(entry_id)
        action = "restored"
    else:
        db.archive_entry(entry_id)
        action = "archived"

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"entry_id": entry_id, "status": action}))
    else:
        output.out_text(f"{action.capitalize()} knowledge entry {entry_id}", ctx.obj)

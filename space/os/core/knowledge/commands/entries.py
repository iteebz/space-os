"""Knowledge entry commands: add, list, query, get, inspect, archive."""

from dataclasses import asdict

import typer

from space.os.core import spawn
from space.os.lib import errors, output

from ..api import entries as api

errors.install_error_handler("knowledge")

app = typer.Typer()


@app.command("add")
def add(
    ctx: typer.Context,
    content: str = typer.Argument(..., help="The knowledge content"),
    domain: str = typer.Option(..., help="Domain of the knowledge"),
    contributor: str = typer.Option(..., "--as", help="Agent identity"),
    confidence: float = typer.Option(None, help="Confidence score (0.0-1.0)"),
):
    """Add a new knowledge entry."""
    agent_id = spawn.ensure_agent(contributor)
    entry_id = api.add_entry(domain, agent_id, content, confidence)
    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"entry_id": entry_id}))
    else:
        output.out_text(
            f"Added knowledge entry {entry_id} for domain '{domain}' by '{contributor}'", ctx.obj
        )


@app.command("list")
def list_entries(
    ctx: typer.Context,
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """List all knowledge entries."""
    entries = api.list_all(include_archived=include_archived)
    if not entries:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json([]))
        else:
            output.out_text("No knowledge entries found.", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(e) for e in entries]))
        return

    output.out_text("Knowledge entries:", ctx.obj)
    domain = None
    for e in entries:
        if e.domain != domain:
            if domain is not None:
                typer.echo()
            output.out_text(f"# {e.domain}", ctx.obj)
            domain = e.domain
        mark = " [ARCHIVED]" if e.archived_at else ""
        contributor = spawn.get_agent_name(e.agent_id) or e.agent_id[:8]
        output.out_text(
            f"[{e.knowledge_id[-8:]}] {e.content[:50]}... ({contributor}){mark}", ctx.obj
        )


@app.command("query")
def query_domain(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain to query"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived"),
):
    """Query knowledge entries by domain."""
    entries = api.query_by_domain(domain, include_archived=include_archived)
    if not entries:
        output.out_text(f"No entries for domain '{domain}'", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(e) for e in entries]))
        return

    output.out_text(f"Domain: {domain} ({len(entries)} entries)", ctx.obj)
    for e in entries:
        mark = " [ARCHIVED]" if e.archived_at else ""
        contributor = spawn.get_agent_name(e.agent_id) or e.agent_id[:8]
        conf = f" [confidence: {e.confidence:.2f}]" if e.confidence else ""
        output.out_text(
            f"[{e.knowledge_id[-8:]}] {e.content[:60]}...{conf} ({contributor}){mark}", ctx.obj
        )


@app.command("inspect")
def inspect(
    ctx: typer.Context,
    knowledge_id: str = typer.Argument(..., help="Knowledge ID to inspect"),
):
    """Inspect knowledge entry details."""
    entry = api.get_by_id(knowledge_id)
    if not entry:
        output.out_text(f"Not found: {knowledge_id}", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json(asdict(entry)))
        return

    contributor = spawn.get_agent_name(entry.agent_id) or entry.agent_id
    output.out_text(f"ID: {entry.knowledge_id}", ctx.obj)
    output.out_text(f"Domain: {entry.domain}", ctx.obj)
    output.out_text(f"Contributor: {contributor}", ctx.obj)
    if entry.confidence:
        output.out_text(f"Confidence: {entry.confidence}", ctx.obj)
    output.out_text(f"Created: {entry.created_at}", ctx.obj)
    if entry.archived_at:
        output.out_text(f"Archived: {entry.archived_at}", ctx.obj)
    output.out_text(f"\nContent:\n{entry.content}", ctx.obj)


@app.command("archive")
def archive(
    ctx: typer.Context,
    knowledge_id: str = typer.Argument(..., help="Knowledge ID to archive"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived entry"),
):
    """Archive or restore a knowledge entry."""
    entry = api.get_by_id(knowledge_id)
    if not entry:
        output.out_text(f"Not found: {knowledge_id}", ctx.obj)
        return

    try:
        if restore:
            api.restore_entry(knowledge_id)
            action = "restored"
        else:
            api.archive_entry(knowledge_id)
            action = "archived"
        output.out_text(f"{action} {knowledge_id[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("knowledge", entry.agent_id, "archive/restore", e)
        raise typer.BadParameter(str(e)) from e

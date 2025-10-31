"""Knowledge CLI: Domain-specific Knowledge Base."""

from dataclasses import asdict

import typer

from space.lib import errors, output
from space.os import spawn
from space.os.knowledge import api

errors.install_error_handler("knowledge")

app = typer.Typer(invoke_without_command=True, add_completion=False)


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Contribute to shared truth. Once written, entries are immutable.
    Archive if wrong, add new if refined. Your insights compound collective intelligence."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command("add")
def add(
    ctx: typer.Context,
    content: str = typer.Argument(..., help="The knowledge content"),
    domain: str = typer.Option(..., help="Domain of the knowledge"),
    contributor: str = typer.Option(..., "--as", help="Agent identity"),
    confidence: float = typer.Option(None, help="Confidence score (0.0-1.0)"),
):
    """Create new knowledge entry (--domain required)."""
    agent = spawn.get_agent(contributor)
    agent_id = agent.agent_id if agent else None
    if not agent_id:
        output.out_text(f"Agent not found: {contributor}", ctx.obj)
        return
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
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
):
    """List all knowledge (--all includes archived)."""
    entries = api.list_entries(show_all=show_all)
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
    for e in entries:
        mark = " [ARCHIVED]" if e.archived_at else ""
        agent = spawn.get_agent(e.agent_id)
        contributor = agent.identity if agent else e.agent_id[:8]
        output.out_text(
            f"[{e.knowledge_id[-8:]}] {e.content[:50]}... ({contributor}){mark}", ctx.obj
        )


@app.command("query")
def query_domain(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain to query"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
):
    """Find entries for specific domain."""
    entries = api.query_by_domain(domain, show_all=show_all)
    if not entries:
        output.out_text(f"No entries for domain '{domain}'", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(e) for e in entries]))
        return

    output.out_text(f"Domain: {domain} ({len(entries)} entries)", ctx.obj)
    for e in entries:
        mark = " [ARCHIVED]" if e.archived_at else ""
        agent = spawn.get_agent(e.agent_id)
        contributor = agent.identity if agent else e.agent_id[:8]
        conf = f" [confidence: {e.confidence:.2f}]" if e.confidence else ""
        output.out_text(
            f"[{e.knowledge_id[-8:]}] {e.content[:60]}...{conf} ({contributor}){mark}", ctx.obj
        )


@app.command("inspect")
def inspect(
    ctx: typer.Context,
    knowledge_id: str = typer.Argument(..., help="Knowledge ID to inspect"),
):
    """View full entry details."""
    entry = api.get_by_id(knowledge_id)
    if not entry:
        output.out_text(f"Not found: {knowledge_id}", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json(asdict(entry)))
        return

    agent = spawn.get_agent(entry.agent_id)
    contributor = agent.identity if agent else entry.agent_id
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
    """Archive or restore knowledge (--restore)."""
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


def main() -> None:
    """Entry point for knowledge command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


__all__ = ["app", "main"]

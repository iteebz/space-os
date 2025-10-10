import json
from dataclasses import asdict

import typer

from ..lib import readme
from . import db

app = typer.Typer(invoke_without_command=True)


@app.callback()
def main_command(
    ctx: typer.Context,
):
    if ctx.resilient_parsing or ctx.invoked_subcommand is None:
        try:
            protocol_content = readme.load_section("# knowledge")
            typer.echo(protocol_content)
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"❌ knowledge section not found in README: {e}")
    return


@app.command("add")
def add_knowledge_command(
    domain: str = typer.Option(..., help="Domain of the knowledge"),
    contributor: str = typer.Option(..., help="Contributor of the knowledge"),
    content: str = typer.Argument(..., help="The knowledge content"),
    confidence: float = typer.Option(None, help="Confidence score (0.0-1.0)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Add a new knowledge entry."""
    entry_id = db.write_knowledge(domain, contributor, content, confidence)
    if json_output:
        typer.echo(json.dumps({"entry_id": entry_id}))
    elif not quiet_output:
        typer.echo(f"Added knowledge entry {entry_id} for domain '{domain}' by '{contributor}'")


@app.command("list")
def list_knowledge_command(
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """List all knowledge entries."""
    entries = db.list_all(include_archived=include_archived)
    if not entries:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo("No knowledge entries found.")
        return

    if json_output:
        typer.echo(json.dumps([asdict(entry) for entry in entries]))
    elif not quiet_output:
        for entry in entries:
            typer.echo(
                f"[{entry.id[-8:]}] [{entry.created_at}] Domain: {entry.domain}, "
                f"Contributor: {entry.contributor}, Confidence: {entry.confidence or 'N/A'}\n"
                f"  Content: {entry.content[:100]}{'...' if len(entry.content) > 100 else ''}\n"
            )


@app.command("about")
def query_by_domain_command(
    domain: str = typer.Argument(..., help="Domain to query knowledge by"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Query knowledge entries by domain."""
    entries = db.query_by_domain(domain, include_archived=include_archived)
    if not entries:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo(f"No knowledge entries found for domain '{domain}'.")
        return

    if json_output:
        typer.echo(json.dumps([asdict(entry) for entry in entries]))
    elif not quiet_output:
        for entry in entries:
            typer.echo(
                f"[{entry.id[-8:]}] [{entry.created_at}] Contributor: {entry.contributor}, "
                f"Confidence: {entry.confidence or 'N/A'}\n"
                f"  Content: {entry.content[:100]}{'...' if len(entry.content) > 100 else ''}\n"
            )


@app.command("from")
def query_by_contributor_command(
    contributor: str = typer.Argument(..., help="Contributor to query knowledge by"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Query knowledge entries by contributor."""
    entries = db.query_by_contributor(contributor, include_archived=include_archived)
    if not entries:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo(f"No knowledge entries found for contributor '{contributor}'.")
        return

    if json_output:
        typer.echo(json.dumps([asdict(entry) for entry in entries]))
    elif not quiet_output:
        for entry in entries:
            typer.echo(
                f"[{entry.id[-8:]}] [{entry.created_at}] Domain: {entry.domain}, "
                f"Confidence: {entry.confidence or 'N/A'}\n"
                f"  Content: {entry.content[:100]}{'...' if len(entry.content) > 100 else ''}\n"
            )


@app.command("get")
def get_knowledge_by_id_command(
    entry_id: str = typer.Argument(..., help="UUID of the knowledge entry"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Get a knowledge entry by its UUID."""
    entry = db.get_by_id(entry_id)
    if not entry:
        if json_output:
            typer.echo(json.dumps(None))
        elif not quiet_output:
            typer.echo(f"No knowledge entry found with ID '{entry_id}'.")
        return

    if json_output:
        typer.echo(json.dumps(asdict(entry)))
    elif not quiet_output:
        typer.echo(
            f"ID: {entry.id}\n"
            f"Created At: {entry.created_at}\n"
            f"Domain: {entry.domain}\n"
            f"Contributor: {entry.contributor}\n"
            f"Confidence: {entry.confidence or 'N/A'}\n"
            f"Content:\n{entry.content}\n"
        )


@app.command("inspect")
def inspect_knowledge_command(
    entry_id: str = typer.Argument(..., help="UUID of the knowledge entry"),
    limit: int = typer.Option(5, help="Number of related entries to show"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived in related"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Inspect entry and find related nodes via keyword similarity."""
    entry = db.get_by_id(entry_id)
    if not entry:
        if json_output:
            typer.echo(json.dumps(None))
        elif not quiet_output:
            typer.echo(f"No knowledge entry found with ID '{entry_id}'.")
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
        typer.echo(f"[{entry.id[-8:]}] {entry.domain} by {entry.contributor}{archived_mark}")
        typer.echo(f"Created: {entry.created_at}")
        typer.echo(f"Confidence: {entry.confidence or 'N/A'}\n")
        typer.echo(f"{entry.content}\n")

        if related:
            typer.echo("─" * 60)
            typer.echo(f"Related nodes ({len(related)}):\n")
            for rel_entry, overlap in related:
                archived_mark = " [ARCHIVED]" if rel_entry.archived_at else ""
                typer.echo(
                    f"[{rel_entry.id[-8:]}] {rel_entry.domain} ({overlap} keywords){archived_mark}"
                )
                typer.echo(
                    f"  {rel_entry.content[:100]}{'...' if len(rel_entry.content) > 100 else ''}\n"
                )


@app.command("archive")
def archive_knowledge_command(
    entry_id: str = typer.Argument(..., help="UUID of the knowledge entry"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived entry"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Archive or restore a knowledge entry."""
    if restore:
        db.restore_entry(entry_id)
        action = "restored"
    else:
        db.archive_entry(entry_id)
        action = "archived"

    if json_output:
        typer.echo(json.dumps({"entry_id": entry_id, "status": action}))
    elif not quiet_output:
        typer.echo(f"{action.capitalize()} knowledge entry {entry_id}")


def main() -> None:
    """Entry point for poetry script."""
    app()

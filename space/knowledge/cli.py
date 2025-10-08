import typer

from . import db
from ..lib import protocols

app = typer.Typer(invoke_without_command=True)

# Removed: PROTOCOL_FILE definition


@app.callback()
def main_command(
    contributor: str = typer.Option(None, "--as", help="Contributor identity"),
    domain: str = typer.Option(None, help="Knowledge domain"),
    from_contributor: str = typer.Option(None, "--from", help="Query by contributor"),
    content: str = typer.Argument(None),
):
    """Knowledge primitive - agent-contributed learned patterns."""
    if not any([content, contributor, domain, from_contributor]):
        try:
            protocol_content = protocols.load("knowledge")
            typer.echo(protocol_content)
        except FileNotFoundError:
            typer.echo("❌ knowledge.md protocol not found")
        return

    if content and contributor and domain:
        entry_id = db.write_knowledge(domain, contributor, content)
        typer.echo(f"Knowledge written: {entry_id[:8]}")
        return

    if domain:
        entries = db.query_by_domain(domain)
        if not entries:
            typer.echo(f"No knowledge for domain: {domain}")
            return

        typer.echo(f"Knowledge in domain '{domain}':")
        for entry in entries:
            typer.echo(f"\n[{entry.id[:8]}] {entry.contributor} | {entry.created_at}")
            typer.echo(entry.content)
        return

    if from_contributor:
        entries = db.query_by_contributor(from_contributor)
        if not entries:
            typer.echo(f"No knowledge from: {from_contributor}")
            return

        typer.echo(f"Knowledge from '{from_contributor}':")
        for entry in entries:
            typer.echo(f"\n[{entry.id[:8]}] {entry.domain} | {entry.created_at}")
            typer.echo(entry.content)
        return

    entries = db.list_all()
    if not entries:
        typer.echo("No knowledge entries found")
        return

    typer.echo(f"{'ID':<10} {'DOMAIN':<15} {'CONTRIBUTOR':<15} {'CREATED':<20}")
    typer.echo("-" * 70)
    for entry in entries:
        typer.echo(
            f"{entry.id[:8]:<10} {entry.domain:<15} {entry.contributor:<15} {entry.created_at:<20}"
        )


@app.command()
def export(
    domain: str = typer.Option(None, help="Filter by domain"),
    from_contributor: str = typer.Option(None, "--from", help="Filter by contributor"),
):
    """Export knowledge entries as markdown."""
    if domain:
        entries = db.query_by_domain(domain)
        title = f"Knowledge: {domain}"
    elif from_contributor:
        entries = db.query_by_contributor(from_contributor)
        title = f"Knowledge from {from_contributor}"
    else:
        entries = db.list_all()
        title = "All Knowledge"

    if not entries:
        typer.echo("No entries found", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"# {title}\n")
    for entry in entries:
        typer.echo(f"## [{entry.id[:8]}] {entry.domain}")
        typer.echo(f"**Contributor:** {entry.contributor}")
        typer.echo(f"**Created:** {entry.created_at}")
        if entry.confidence:
            typer.echo(f"**Confidence:** {entry.confidence}")
        typer.echo(f"\n{entry.content}\n")
        typer.echo("---\n")


@app.command()
def show(entry_id: str = typer.Argument(..., help="Show single knowledge entry.")):
    """Show single knowledge entry."""
    entry = db.get_by_id(entry_id)
    if not entry:
        typer.echo(f"Entry not found: {entry_id}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"ID: {entry.id}")
    typer.echo(f"Domain: {entry.domain}")
    typer.echo(f"Contributor: {entry.contributor}")
    typer.echo(f"Created: {entry.created_at}")
    if entry.confidence:
        typer.echo(f"Confidence: {entry.confidence}")
    typer.echo(f"\n{entry.content}")


if __name__ == "__main__":
    app()

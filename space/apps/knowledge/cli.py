import click

from . import (
    write_knowledge,
    query_knowledge,
)


@click.group(name="knowledge")
def knowledge_group():
    """Knowledge primitive - agent-contributed learned patterns."""
    pass


@knowledge_group.command(name="write")
@click.option("--as", "contributor", help="Contributor identity", required=True)
@click.option("--domain", help="Knowledge domain", required=True)
@click.argument("content")
def write_knowledge_command(contributor, domain, content):
    """Write a knowledge entry."""
    entry_id = write_knowledge(domain, contributor, content)
    click.echo(f"Knowledge written: {entry_id[:8]}")


@knowledge_group.command(name="query")
@click.option("--domain", help="Filter by domain")
@click.option("--contributor", help="Filter by contributor")
@click.option("--id", "entry_id", help="Query by entry ID")
def query_knowledge_command(domain, contributor, entry_id):
    """Query knowledge entries."""
    entries = query_knowledge(domain=domain, contributor=contributor, entry_id=entry_id)
    if not entries:
        click.echo("No knowledge entries found")
        return

    # ... (rest of the query command logic can be simplified or kept as is)
    if entry_id and len(entries) == 1:
        entry = entries[0]
        click.echo(f"ID: {entry.id}")
        click.echo(f"Domain: {entry.domain}")
        click.echo(f"Contributor: {entry.contributor}")
        click.echo(f"Created: {entry.created_at}")
        if entry.confidence:
            click.echo(f"Confidence: {entry.confidence}")
        click.echo(f"\n{entry.content}")
    else:
        click.echo(f"{'ID':<10} {'DOMAIN':<15} {'CONTRIBUTOR':<15} {'CREATED':<20}")
        click.echo("---" * 23 + "\n")
        for entry in entries:
            click.echo(
                f"{entry.id[:8]:<10} {entry.domain:<15} {entry.contributor:<15} {entry.created_at:<20}"
            )



import sys

import click

from space.lib.storage import knowledge as storage


@click.group(invoke_without_command=True)
@click.pass_context
def knowledge_group(ctx):
    """Knowledge primitive - agent-contributed learned patterns."""
    if ctx.invoked_subcommand is None:
        # If no subcommand is invoked, we'll call the 'query' command
        ctx.invoke(query_knowledge)


@knowledge_group.command(name="query")
@click.option("--as", "contributor", help="Contributor identity")
@click.option("--domain", help="Knowledge domain")
@click.option("--from", "from_contributor", help="Query by contributor")
@click.argument("content", required=False)
def query_knowledge(contributor, domain, from_contributor, content):
    if content and contributor and domain:
        entry_id = storage.write_knowledge(domain, contributor, content)
        click.echo(f"Knowledge written: {entry_id[:8]}")
        return

    if domain:
        entries = storage.query_by_domain(domain)
        if not entries:
            click.echo(f"No knowledge for domain: {domain}")
            return

        click.echo(f"Knowledge in domain '{domain}':")
        for entry in entries:
            click.echo(f"\n[{entry.id[:8]}] {entry.contributor} | {entry.created_at}")
            click.echo(entry.content)
        return

    if from_contributor:
        entries = storage.query_by_contributor(from_contributor)
        if not entries:
            click.echo(f"No knowledge from: {from_contributor}")
            return

        click.echo(f"Knowledge from '{from_contributor}':")
        for entry in entries:
            click.echo(f"\n[{entry.id[:8]}] {entry.domain} | {entry.created_at}")
            click.echo(entry.content)
        return

    entries = storage.list_all()
    if not entries:
        click.echo("No knowledge entries found")
        return

    click.echo(f"{'ID':<10} {'DOMAIN':<15} {'CONTRIBUTOR':<15} {'CREATED':<20}")
    click.echo("-" * 70)
    for entry in entries:
        click.echo(
            f"{entry.id[:8]:<10} {entry.domain:<15} {entry.contributor:<15} {entry.created_at:<20}"
        )


@knowledge_group.command()
@click.option("--domain", help="Filter by domain")
@click.option("--from", "from_contributor", help="Filter by contributor")
def export(domain, from_contributor):
    """Export knowledge entries as markdown."""
    if domain:
        entries = storage.query_by_domain(domain)
        title = f"Knowledge: {domain}"
    elif from_contributor:
        entries = storage.query_by_contributor(from_contributor)
        title = f"Knowledge from {from_contributor}"
    else:
        entries = storage.list_all()
        title = "All Knowledge"

    if not entries:
        click.echo("No entries found", err=True)
        sys.exit(1)

    click.echo(f"# {title}\n")
    for entry in entries:
        click.echo(f"## [{entry.id[:8]}] {entry.domain}")
        click.echo(f"**Contributor:** {entry.contributor}")
        click.echo(f"**Created:** {entry.created_at}")
        if entry.confidence:
            click.echo(f"**Confidence:** {entry.confidence}")
        click.echo(f"\n{entry.content}\n")
        click.echo("---\n")


@knowledge_group.command()
@click.argument("entry_id")
def show(entry_id):
    """Show single knowledge entry."""
    entry = storage.get_by_id(entry_id)
    if not entry:
        click.echo(f"Entry not found: {entry_id}", err=True)
        sys.exit(1)

    click.echo(f"ID: {entry.id}")
    click.echo(f"Domain: {entry.domain}")
    click.echo(f"Contributor: {entry.contributor}")
    click.echo(f"Created: {entry.created_at}")
    if entry.confidence:
        click.echo(f"Confidence: {entry.confidence}")
    click.echo(f"\n{entry.content}")

import sys

import click

from space.os.lib.base64 import decode_b64
from space.os import events
from space.apps.registry import api as registry_api

from . import knowledge
from .app import knowledge_app as app


@click.group(invoke_without_command=True, name="knowledge")
@click.pass_context
def knowledge_group(ctx):
    """Knowledge primitive - agent-contributed learned patterns."""
    if ctx.invoked_subcommand is None:
        knowledge_guide_content = register_api.load_guide_content("knowledge")
        if knowledge_guide_content:
            events.track("knowledge", knowledge_guide_content)
            click.echo(knowledge_guide_content)
        else:
            click.echo("No knowledge guide found. Create space/apps/knowledge/prompts/guides/knowledge.md")
        return


@knowledge_group.command(name="write")
@click.option("--as", "contributor", help="Contributor identity")
@click.option("--domain", help="Knowledge domain")
@click.argument("content")
def write_knowledge_command(contributor, domain, content):
    """Write a knowledge entry."""
    if not contributor or not domain:
        raise click.UsageError("--as and --domain are required when writing.")
    entry_id = knowledge.write(domain, contributor, content)
    click.echo(f"Knowledge written: {entry_id[:8]}")


@knowledge_group.command(name="query")
@click.option("--domain", help="Filter by domain")
@click.option("--contributor", help="Filter by contributor")
@click.option("--id", "entry_id", help="Query by entry ID")
def query_knowledge_command(domain, contributor, entry_id):
    """Query knowledge entries."""
    entries = knowledge.query(domain=domain, contributor=contributor, entry_id=entry_id)
    if not entries:
        click.echo("No knowledge entries found")
        return

    if entry_id:
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


@knowledge_group.command()
@click.option("--domain", help="Filter by domain")
@click.option("--contributor", help="Filter by contributor")
def export(domain, contributor):
    """Export knowledge entries as markdown."""
    entries = knowledge.query(domain=domain, contributor=contributor)
    if not entries:
        click.echo("No entries found", err=True)
        sys.exit(1)

    title = "All Knowledge"
    if domain:
        title = f"Knowledge: {domain}"
    elif contributor:
        title = f"Knowledge from {contributor}"

    click.echo(f"# {title}\n")
    for entry in entries:
        click.echo(f"## [{entry.id[:8]}] {entry.domain}")
        click.echo(f"**Contributor:** {entry.contributor}")
        click.echo(f"**Created:** {entry.created_at}")
        if entry.confidence:
            click.echo(f"**Confidence:** {entry.confidence}")
        click.echo(f"\n{entry.content}\n")
        click.echo("---")


@knowledge_group.command()
@click.argument("entry_id")
def show(entry_id):
    """Show single knowledge entry."""
    entries = knowledge.query(entry_id=entry_id)
    if not entries:
        click.echo(f"Entry not found: {entry_id}", err=True)
        sys.exit(1)

    entry = entries[0]
    click.echo(f"ID: {entry.id}")
    click.echo(f"Domain: {entry.domain}")
    click.echo(f"Contributor: {entry.contributor}")
    click.echo(f"Created: {entry.created_at}")
    if entry.confidence:
        click.echo(f"Confidence: {entry.confidence}")
    click.echo(f"\n{entry.content}")

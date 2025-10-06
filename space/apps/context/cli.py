import sys

import click

from space import events
from space.lib import fs
from space.lib.base64 import decode_b64

from . import knowledge, memory

GUIDE_FILE = fs.guide_path("memory.md")


@click.group()
def context_group():
    """Context primitive - memory and knowledge."""
    pass


@context_group.command("memory")
@click.option("--as", "identity", help="Identity name")
@click.option("--topic", help="Topic name")
@click.option("--clear", is_flag=True, help="Clear entries")
@click.option("--edit", metavar="UUID", help="Edit entry by UUID")
@click.option("--delete", metavar="UUID", help="Delete entry by UUID")
@click.option("--base64", "decode_base64", is_flag=True, help="Decode base64 payload")
@click.argument("message", required=False)
def memory(identity, topic, clear, edit, delete, decode_base64, message):
    """Memory primitive - agent-contributed learned patterns."""
    if GUIDE_FILE.exists():
        events.track("memory", GUIDE_FILE.read_text())

    all_options_are_default = (
        not identity and not topic and not clear and not edit and not delete and not message
    )
    if all_options_are_default:
        if GUIDE_FILE.exists():
            click.echo(GUIDE_FILE.read_text())
        else:
            click.echo("memory.md not found")
        return

    if not identity:
        click.echo("No identity provided. Use 'space memory --help' for options.")
        return

    if clear:
        memory.clear(identity, topic)
        scope = f"topic '{topic}'" if topic else "all topics"
        click.echo(f"Cleared {scope} for {identity}")
        return

    if edit is not None:
        if not message:
            raise click.UsageError("message required when editing")
        if decode_base64:
            message = decode_b64(message)
        try:
            memory.edit(edit, message)
        except ValueError as e:
            raise click.UsageError(str(e)) from e
        return

    if delete is not None:
        try:
            memory.delete(delete)
            click.echo(f"Deleted entry {delete}")
        except ValueError as e:
            raise click.UsageError(str(e)) from e
        return

    if message:
        if not topic:
            raise click.UsageError("--topic required when writing")
        if decode_base64:
            message = decode_b64(message)
        memory.memorize(identity, topic, message)
        return

    entries = memory.recall(identity, topic)
    if not entries:
        scope = f"topic '{topic}'" if topic else "all topics"
        click.echo(f"No entries found for {identity} in {scope}")
        return

    current_topic = None
    for e in entries:
        if e.topic != current_topic:
            if current_topic is not None:
                click.echo()
            click.echo(f"# {e.topic}")
            current_topic = e.topic
        click.echo(f"[{e.uuid[-8:]}] [{e.timestamp}] {e.message}")


@context_group.group(invoke_without_command=True, name="knowledge")
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
        entry_id = knowledge.write(domain, contributor, content)
        click.echo(f"Knowledge written: {entry_id[:8]}")
        return

    if domain:
        entries = knowledge.query(domain=domain)
        if not entries:
            click.echo(f"No knowledge for domain: {domain}")
            return

        click.echo(f"Knowledge in domain '{domain}':")
        for entry in entries:
            click.echo(f"\n[{entry.id[:8]}] {entry.contributor} | {entry.created_at}")
            click.echo(entry.content)
        return

    if from_contributor:
        entries = context.knowledge.query_by_contributor(from_contributor)
        if not entries:
            click.echo(f"No knowledge from: {from_contributor}")
            return

        click.echo(f"Knowledge from '{from_contributor}':")
        for entry in entries:
            click.echo(f"\n[{entry.id[:8]}] {entry.domain} | {entry.created_at}")
            click.echo(entry.content)
        return

    entries = knowledge.query()
    if not entries:
        click.echo("No knowledge entries found")
        return

    click.echo(f"{'ID':<10} {'DOMAIN':<15} {'CONTRIBUTOR':<15} {'CREATED':<20}")
    click.echo("---" * 23 + "\n")
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
        entries = context.knowledge.query_by_domain(domain)
        title = f"Knowledge: {domain}"
    elif from_contributor:
        entries = context.knowledge.query_by_contributor(from_contributor)
        title = f"Knowledge from {from_contributor}"
    else:
        entries = knowledge.query()
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
    entry = knowledge.query(entry_id=entry_id)
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

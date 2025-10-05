from pathlib import Path

import click

from .. import protocols
from . import storage


PROTOCOL_FILE = Path(__file__).parent.parent.parent / "prompts" / "memory.md"
if PROTOCOL_FILE.exists():
    protocols.track("memory", PROTOCOL_FILE.read_text())


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--as", "identity", required=True, help="Identity name")
@click.option("--topic", help="Topic name")
@click.option("--clear", is_flag=True, help="Clear entries")
@click.option("--edit", metavar="UUID", help="Edit entry by UUID")
@click.option("--delete", metavar="UUID", help="Delete entry by UUID")
@click.argument("message", required=False)
def main(ctx, identity, topic, clear, edit, delete, message):
    if ctx.invoked_subcommand:
        return

    if clear:
        storage.clear_entries(identity, topic)
        scope = f"topic '{topic}'" if topic else "all topics"
        click.echo(f"Cleared {scope} for {identity}")
        return

    if edit is not None:
        if not message:
            raise click.UsageError("message required when editing")
        storage.edit_entry(edit, message)
        click.echo(f"Edited entry {edit}")
        return

    if delete is not None:
        storage.delete_entry(delete)
        click.echo(f"Deleted entry {delete}")
        return

    if message:
        if not topic:
            raise click.UsageError("--topic required when writing")
        storage.add_entry(identity, topic, message)
        return

    entries = storage.get_entries(identity, topic)
    if not entries:
        return

    current_topic = None
    for e in entries:
        if e.topic != current_topic:
            if current_topic is not None:
                click.echo()
            click.echo(f"# {e.topic}")
            current_topic = e.topic
        click.echo(f"[{e.uuid[:8]}] [{e.timestamp}] {e.message}")

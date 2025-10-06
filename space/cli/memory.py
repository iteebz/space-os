import click

import space.protocols as protocols
from space.lib import fs
from space.lib.base64 import decode_b64
from space.lib.storage import memory as storage

GUIDE_FILE = fs.guide_path("memory.md")


@click.command("memory")
@click.option("--as", "identity", help="Identity name")
@click.option("--topic", help="Topic name")
@click.option("--clear", is_flag=True, help="Clear entries")
@click.option("--edit", metavar="UUID", help="Edit entry by UUID")
@click.option("--delete", metavar="UUID", help="Delete entry by UUID")
@click.option("--base64", "decode_base64", is_flag=True, help="Decode base64 payload")
@click.argument("message", required=False)
def memory_group(identity, topic, clear, edit, delete, decode_base64, message):
    """Memory primitive - agent-contributed learned patterns."""
    if GUIDE_FILE.exists():
        protocols.track("memory", GUIDE_FILE.read_text())

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
        storage.clear_entries(identity, topic)
        scope = f"topic '{topic}'" if topic else "all topics"
        click.echo(f"Cleared {scope} for {identity}")
        return

    if edit is not None:
        if not message:
            raise click.UsageError("message required when editing")
        if decode_base64:
            message = decode_b64(message)
        try:
            storage.edit_entry(edit, message)
        except ValueError as e:
            raise click.UsageError(str(e)) from e
        return

    if delete is not None:
        try:
            storage.delete_entry(delete)
            click.echo(f"Deleted entry {delete}")
        except ValueError as e:
            raise click.UsageError(str(e)) from e
        return

    if message:
        if not topic:
            raise click.UsageError("--topic required when writing")
        if decode_base64:
            message = decode_b64(message)
        storage.add_entry(identity, topic, message)
        return

    entries = storage.get_entries(identity, topic)
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

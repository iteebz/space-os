import click
from pathlib import Path

from space.os.lib.base64 import decode_b64

from . import memory
from space.apps.register import api as register_api
from space.os import events


@click.group(invoke_without_command=True)
@click.pass_context
def memory_group(ctx):
    """Memory primitive - agent-contributed learned patterns."""
    if ctx.invoked_subcommand is None:
        guide_path = Path(__file__).parent / "memory.md"
        if guide_path.exists():
            click.echo(guide_path.read_text())
        return


@memory_group.command("add")
@click.option("--as", "identity", required=True, help="Identity name")
@click.option("--topic", required=True, help="Topic name")
@click.option("--base64", "decode_base64", is_flag=True, help="Decode base64 payload")
@click.argument("message")
def add_memory(identity, topic, decode_base64, message):
    """Memorize a message."""
    if decode_base64:
        message = decode_b64(message)
    memory.memorize(identity, topic, message)


@memory_group.command("recall")
@click.option("--as", "identity", required=True, help="Identity name")
@click.option("--topic", help="Topic name")
def recall_memory(identity, topic):
    """Recall messages for a topic."""
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


@memory_group.command("clear")
@click.option("--as", "identity", required=True, help="Identity name")
@click.option("--topic", help="Topic name")
def clear_memory(identity, topic):
    """Clear memory entries."""
    memory.clear(identity, topic)
    scope = f"topic '{topic}'" if topic else "all topics"
    click.echo(f"Cleared {scope} for {identity}")


@memory_group.command("edit")
@click.option("--as", "identity", required=True, help="Identity name")
@click.option("--base64", "decode_base64", is_flag=True, help="Decode base64 payload")
@click.argument("uuid")
@click.argument("message")
def edit_memory(identity, decode_base64, uuid, message):
    """Edit a memory entry by UUID."""
    if decode_base64:
        message = decode_b64(message)
    try:
        memory.edit(uuid, message)
    except ValueError as e:
        raise click.UsageError(str(e)) from e


@memory_group.command("delete")
@click.option("--as", "identity", required=True, help="Identity name")
@click.argument("uuid")
def delete_memory(identity, uuid):
    """Delete a memory entry by UUID."""
    try:
        memory.delete(uuid)
        click.echo(f"Deleted entry {uuid}")
    except ValueError as e:
        raise click.UsageError(str(e)) from e

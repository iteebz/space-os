import click

from space.os.lib.base64 import decode_b64
from space.os import events
from space.apps.register import api as register_api

from . import memory, app


@click.group(invoke_without_command=True)
@click.pass_context
def memory_group(ctx):
    """Memory primitive - agent-contributed learned patterns."""
    if ctx.invoked_subcommand is None:
        memory_guide_content = register_api.load_guide_content("memory")
        if memory_guide_content:
            events.track("memory", memory_guide_content)
            click.echo(memory_guide_content)
        else:
            click.echo("No memory guide found. Create space/apps/memory/prompts/guides/memory.md")
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
    memory.memorize(app.db_path, identity, topic, message)


@memory_group.command("recall")
@click.option("--as", "identity", required=True, help="Identity name")
@click.option("--topic", help="Topic name")
def recall_memory(identity, topic):
    """Recall messages for a topic."""
    entries = memory.recall(app.db_path, identity, topic)
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
    memory.clear(app.db_path, identity, topic)
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
        memory.edit(app.db_path, uuid, message)
    except ValueError as e:
        raise click.UsageError(str(e)) from e


@memory_group.command("delete")
@click.option("--as", "identity", required=True, help="Identity name")
@click.argument("uuid")
def delete_memory(identity, uuid):
    """Delete a memory entry by UUID."""
    try:
        memory.delete(app.db_path, uuid)
    except ValueError as e:
        raise click.UsageError(str(e)) from e

import click

from . import create_channel, get_channel_id, create_message, get_messages_for_channel

@click.group()
def bridge_group():
    """Bridge: AI Coordination Protocol"""
    pass

@bridge_group.command()
@click.argument('channel_name')
@click.argument('content')
@click.option('--as', 'identity', default='human')
def send(channel_name, content, identity):
    """Send a message to a channel."""
    channel_id = get_channel_id(channel_name)
    if not channel_id:
        channel_id = create_channel(channel_name, "")
    
    create_message(channel_id, identity, content, "")
    click.echo(f"Sent message to {channel_name}")

@bridge_group.command()
@click.argument('channel_name')
def recv(channel_name):
    """Receive messages from a channel."""
    channel_id = get_channel_id(channel_name)
    if not channel_id:
        click.echo(f"Channel {channel_name} not found.")
        return
    
    messages = get_messages_for_channel(channel_id)
    for msg in messages:
        click.echo(f"[{msg.sender}] {msg.content}")
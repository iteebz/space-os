"""Bridge CLI commands: typer entry points only.

Modules: channels, messages, notes, export (one per domain).
Patterns: parse args, call ops functions, format output, emit events.
Zero business logic—delegated to ops/.
"""

import typer

from space.lib import output, readme

from . import channels, export, messages, notes

app = typer.Typer(invoke_without_command=True)
app.add_typer(channels.app, name="channels")
app.add_typer(messages.app, name="messages")
app.add_typer(notes.app, name="notes")


@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Bridge: Channel Communications"""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo(readme.load("bridge"))


@app.command("list")
def list_cmd(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    all: bool = typer.Option(False, "--all", help="Include archived channels"),
):
    """List channels."""
    channels.list_channels_cmd(ctx, identity, all)


@app.command("send")
def send_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option("human", "--as", help="Identity (defaults to human)"),
    decode_base64: bool = typer.Option(False, "--base64", help="Decode base64 payload"),
):
    """Send message."""
    messages.send_cmd(ctx, channel, content, identity, decode_base64)


@app.command("recv")
def recv_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity to receive as"),
):
    """Receive messages."""
    messages.recv_cmd(ctx, channel, identity)


@app.command("inbox")
def inbox_cmd(
    ctx: typer.Context,
    identity: str = typer.Option(..., "--as", help="Identity"),
):
    """Inbox."""
    messages.inbox(ctx, identity)


@app.command("export")
def export_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    identity: str | None = typer.Option(None, "--as", help="Agent identity"),
):
    """Export channel."""
    export.export_cmd(ctx, channel, identity)

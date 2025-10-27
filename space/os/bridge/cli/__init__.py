"""Bridge CLI: thin command wrappers delegating to ops layer."""

import typer

from space.lib import output
from space.os.bridge import ops

from . import channels, format, messages, notes

app = typer.Typer()


@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Manage channels, messages, and notes."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}
    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo("Run 'bridge --help' for available commands and options.")


@app.command("inbox")
def inbox_cmd(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Show unread channels for an agent (aware of bookmarks)."""
    if not identity:
        format.output_json(
            {"status": "error", "message": "identity required (use --as)"}, ctx
        ) or format.echo_if_output("❌ Error: identity required (use --as)", ctx)
        raise typer.Exit(code=1)

    try:
        chans = ops.fetch_inbox(identity)

        if not chans:
            format.output_json([], ctx) or format.echo_if_output("No unread channels", ctx)
            return

        if format.output_json(
            [
                {
                    "name": c.name,
                    "topic": c.topic,
                    "message_count": c.message_count,
                    "last_activity": c.last_activity,
                    "unread_count": c.unread_count,
                }
                for c in chans
            ],
            ctx,
        ):
            return

        if not format.should_output(ctx):
            return

        format.echo_if_output(f"INBOX ({len(chans)}):", ctx)
        for channel in chans:
            last_activity, description = format.format_channel_row(channel)
            format.echo_if_output(f"  {last_activity}: {description}", ctx)
    except Exception as e:
        format.output_json({"status": "error", "message": str(e)}, ctx) or format.echo_if_output(
            f"❌ {e}", ctx
        )
        raise typer.Exit(code=1) from e


app.add_typer(channels.app, name="channels")
app.add_typer(messages.app, name="messages")
app.add_typer(notes.app, name="notes")

__all__ = ["app"]

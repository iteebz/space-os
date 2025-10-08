"""Bridge CLI - Clean command interface."""

import typer

from ..lib import protocols
from . import api, utils
from .commands import messages as messages_cmds
from .commands.channels import app as channels_app
from .commands.messages import app as messages_app
from .commands.monitor import app as monitor_app

app = typer.Typer(invoke_without_command=True, add_help_option=False)


@app.callback()
def main_command(
    ctx: typer.Context,
    help_flag: bool = typer.Option(
        False,
        "--help",
        "-h",
        help="Show protocol instructions and command overview.",
        is_eager=True,
    ),
):
    """Bridge: AI Coordination Protocol"""
    if help_flag:
        try:
            typer.echo(protocols.load("bridge"))
            typer.echo()
        except FileNotFoundError:
            typer.echo("❌ bridge.md protocol not found")
            typer.echo()
        typer.echo(ctx.command.get_help(ctx))
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        try:
            _print_active_channels()
            typer.echo(protocols.load("bridge"))
        except FileNotFoundError:
            typer.echo("❌ bridge.md protocol not found")
        else:
            typer.echo()


app.add_typer(channels_app, name="channels")
app.add_typer(messages_app, name="messages")
app.add_typer(monitor_app, name="monitor")
app.command("send")(messages_cmds.send)
app.command("recv")(messages_cmds.recv)
app.command("notes")(messages_cmds.notes)
app.command("alert")(messages_cmds.alert)
app.command("export")(messages_cmds.export)


def _print_active_channels():
    """Render active channel list like the original dashboard."""
    try:
        active_channels = api.active_channels()
    except Exception as exc:  # pragma: no cover - defensive logging for CLI usage
        typer.echo(f"⚠️ Unable to load bridge channels: {exc}")
        typer.echo()
        return

    if not active_channels:
        typer.echo("No active bridge channels yet.")
        typer.echo()
        return

    typer.echo("ACTIVE CHANNELS:")
    for channel in active_channels:
        ago = utils.format_time_ago(channel.last_activity)
        meta_str = utils.format_channel_meta(channel)
        typer.echo(f"  {channel.name} - {ago} | {meta_str}")
    typer.echo()


if __name__ == "__main__":
    app()
